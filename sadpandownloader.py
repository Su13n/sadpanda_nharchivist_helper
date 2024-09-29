import os
import sys
import json
from time import sleep
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image
import zipfile
import shutil
import argparse
from tqdm import tqdm
import threading
import re
import glob
import logging
from dotenv import load_dotenv, set_key

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_session(cookies, user_agent):
    session = requests.Session()
    session.headers.update({'User-Agent': user_agent})
    session.cookies.update(cookies)
    return session

def parse_url(url):
    parts = url.split('/')
    gallery_id = parts[-3]
    gallery_token = parts[-2]
    return gallery_id, gallery_token

def make_api_call(session, gallery_id, gallery_token):
    api_url = "https://api.e-hentai.org/api.php"
    payload = {
        "method": "gdata",
        "gidlist": [[gallery_id, gallery_token]],
        "namespace": 1
    }
    response = session.post(api_url, json=payload)
    response.raise_for_status()
    return response.json()

def get_image_url(session, page_url, fullResEnabled):
    response = session.get(page_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for the full image download link
    img_link = soup.find('a', href=re.compile(r'https://e.hentai\.org/fullimg/.*')) if fullResEnabled else soup.find('img', id='img')
    
    if img_link:
        return img_link['href'] if fullResEnabled else img_link['src']
    
    logging.warning(f"No image found on page: {page_url}")
    return None

def extract_image_urls(session, gallery_id, gallery_token, filecount, fullResEnabled):
    base_url = f"https://exhentai.org/g/{gallery_id}/{gallery_token}/"
    image_urls = []
    page_count = (filecount - 1) // 20 + 1  # Calculate the number of pages
    requires_gp = False
    for page in tqdm(range(page_count), desc="Extracting image URLs"):
        url = f"{base_url}?p={page}"
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links that match the image page syntax
        image_page_links = soup.find_all('a', href=re.compile(rf"https://e.hentai\.org/s/[a-z0-9]+/{gallery_id}-\d+"))
        
        for link in image_page_links:
            image_page_url = link['href']
            image_url = get_image_url(session, image_page_url, fullResEnabled)
            if image_url:
                image_urls.append(image_url)

    if len(image_urls) != filecount:
        logging.warning(f"Expected {filecount} images, but found {len(image_urls)}")

    return image_urls

def is_file_complete(local_path, url, session):
    if os.path.exists(local_path):
        local_size = os.path.getsize(local_path)
        server_size = int(session.head(url).headers.get('Content-Length', 0))
        return local_size == server_size
    return False

def download_images(session, image_urls, output_dir, compression):
    for i, url in enumerate(tqdm(image_urls, desc="Downloading images")):
        file_extension = os.path.splitext(url)[1]
        filename = f"{output_dir}/{i+1:03d}{file_extension}"
        rawname = f"{output_dir}/{i+1:03d}*"
        if not glob.glob(rawname):
            for attempt in range (1, 6):
                try:
                    response = session.get(url, stream=True)
                    response.raise_for_status()
                   
                    # Check Content-Type to ensure it’s an image
                    content_type = response.headers.get('Content-Type', '')
                    if 'image' not in content_type:
                        logging.error(f"URL {url} did not return an image. Skipping.")
                        continue

                    if not os.path.exists(filename):
                        # Save the image in chunks to avoid incomplete downloads
                        with open(filename, 'wb') as f:
                            f.write(response.content)

                    # Proceed with compression if enabled
                    if compression['on'] and os.path.exists(filename):
                        t1 = threading.Thread(target=save_as_webp, args=(filename, compression['quality']))
                        t1.start()
                        t1.join()

                except Exception as e:
                    logging.error(f"Error downloading {url}: {str(e)}")

def save_as_webp(original, q):
    try:
        image = Image.open(original)
        filename = os.path.splitext(original)[0] + '.webp'
        image.save(filename, 'webp', optimize=True, quality=q)
        os.remove(original)
    except Exception as e:
        logging.error(f"Error compressing {original}: {str(e)}")

def process_metadata(metadata): #nhentai archive compatibility
    tags = metadata.get('tags', [])
    artist = None
    group = None
    modified_tags = []

    for tag in tags:
        if tag.startswith('artist:'):
            artist = tag.split(':', 1)[1]  # Extract artist name
            continue
        if tag.startswith('group:'):
            group = tag.split(':', 1)[1]  # Extract group name
            continue
        modified_tag = tag.replace(':', ': ')  # Ensure space after colon
        modified_tags.append(modified_tag)

    metadata['tags'] = modified_tags  # Update tags with modified version
    if artist:
        metadata['artist'] = artist  # Add extracted artist
    if group:
        metadata['group'] = group # Add extracted group

    return metadata

def create_comic_info_xml(metadata, output_dir):
    root = ET.Element("ComicInfo")
    ET.SubElement(root, "Title").text = f"{metadata['gid']} {metadata['title']}"
    date = datetime.fromtimestamp(int(metadata['posted']))
    ET.SubElement(root, "Year").text = str(date.year)
    ET.SubElement(root, "Month").text = str(date.month)
    ET.SubElement(root, "Day").text = str(date.day)
    metadata = process_metadata(metadata)
    if 'artist' in metadata:
        ET.SubElement(root, "Writer").text = metadata['artist']
    else:
        ET.SubElement(root, "Writer").text = "Unknown"
    ET.SubElement(root, "Translator")
    if 'group' in metadata:
        ET.SubElement(root, "Publisher").text = metadata['group']
    ET.SubElement(root, "Genre").text = metadata['category'].replace(":", ": ")
    ET.SubElement(root, "Tags").text = ", ".join(metadata['tags'])
    ET.SubElement(root, "Web").text = f"https://exhentai.org/g/{metadata['gid']}/{metadata['token']}/"

    tree = ET.ElementTree(root)
    tree.write(f"{output_dir}/ComicInfo.xml", encoding="utf-8", xml_declaration=True)

def create_cbz(input_dir, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(input_dir):
            for file in files:
                zipf.write(os.path.join(root, file), 
                           os.path.relpath(os.path.join(root, file), 
                                           os.path.join(input_dir, '.')))

def add_env_variables_if_not_exist(env_path):
    variables_to_add = {
        'IGNEOUS': '',
        'IPB_MEMBER_ID': '',
        'IPB_PASS_HASH': '',
        'IPB_SESSION_ID': '',
        'SK': ''
    }

    # Iterate over the variables and add them if they do not exist
    for key, value in variables_to_add.items():
        if os.getenv(key) is None:  # Check if the variable is not set
            set_key(env_path, key, value)  # Add the variable to the .env file


def main(urls, cookies, user_agent, library_path, compression, fullResEnabled):
    session = get_session(cookies, user_agent)
    for url in urls:
        try:
            gallery_id, gallery_token = parse_url(url)
            logging.info(f"Processing gallery: {gallery_id}")

            metadata = make_api_call(session, gallery_id, gallery_token)['gmetadata'][0]
            filecount = int(metadata['filecount'])
            gallery_name = metadata['title']

            image_urls = extract_image_urls(session, gallery_id, gallery_token, filecount, fullResEnabled)

            if not image_urls:
                logging.error(f"No images found for gallery {gallery_id}. Skipping.")
                continue

            temp_dir = f"{library_path}{gallery_id}"
            os.makedirs(temp_dir, exist_ok=True)
            
            create_comic_info_xml(metadata, temp_dir)
            download_images(session, image_urls, temp_dir, compression)
            

            output_dir = f"{library_path}sadpanda"
            os.makedirs(output_dir, exist_ok=True)
            cbz_file = f"{output_dir}/{gallery_id} {gallery_name}.cbz"
            cbz_file = cbz_file.translate({ord(i): None for i in ':*?"<>|'})
            print(f'cbz: {cbz_file}')
            create_cbz(temp_dir, cbz_file)

            shutil.rmtree(temp_dir)
            logging.info(f"Successfully created {cbz_file}")

        except Exception as e:
            logging.error(f"Error processing {url}: {str(e)}", exc_info=True)

def load_env_variables():
    env_path = './config/.env'
    load_dotenv(env_path)
    add_env_variables_if_not_exist(env_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sadpanda Gallery Downloader")
    parser.add_argument("-u", "--urls", nargs="*", help="URLs to process")
    parser.add_argument("-f", "--file", action='store_true', help="Mass download galleries listed in ./config/sadpandaurls.txt")
    parser.add_argument("-w", "--webp", action='store_true', help="Toggle .webp conversion.")
    parser.add_argument("-q", "--quality", type=int, default=100, help="Convert images to .webp at chosen quality (90 is recommended for minimal quality degradation)")
    parser.add_argument("--full-resolution", action='store_true', help="Toggles full-res download requiring GP.")
    args = parser.parse_args()
    
    urls_path = './config/sadpandaurls.txt'
    
    if not os.path.exists(urls_path):
        with open(urls_path, 'w') as u:
            u.write('Place your exhentai links here.')
    
    if args.urls:
        urls = args.urls
    else:
        urls = []
    
    if args.file:
        with open(urls_path, 'r') as f:
            urls.extend(f.read().splitlines())
        
    fullResEnabled = True if args.full_resolution else False
    
    load_env_variables()
    
    cookies = {
        "igneous": os.getenv('IGNEOUS'),
        "ipb_member_id": os.getenv('IPB_MEMBER_ID'),
        "ipb_pass_hash": os.getenv('IPB_PASS_HASH'),
        "ipb_session_id": os.getenv('IPB_SESSION_ID'),
        "sk": os.getenv('SK')
    }
            
    compression = {
        "on" : args.webp,
        "quality" : args.quality
    }
    
    if args.quality:
        q = args.quality
        logging.info(f'Quality: {q}')
        if q >= 0 and q <=100:
            main(urls, cookies, os.getenv('USER_AGENT'), os.getenv('LIBRARY_PATH'), compression, fullResEnabled)
        else:
            logging.error(f"Quality {q} is invalid (0-100).")

    