# sadpanda_nharchivist_helper
Python script allowing you to download galleries from sadpanda directly into your [nhentai_archivist](https://github.com/9-FS/nhentai_archivist) database in .cbz format and with [Komga](https://komga.org/) compatibility, e.g., to archive doujins that have been excluded from nhentai (like purged stuff or works containing certain tags like 'furry').

## Quick Start

1. Make sure you have sufficient GP on your e-hentai account to download full-size images.
2. Place the executable next to your nhentai_archivist.exe
3. Execute the program once to add missing variables to your `./config/.env`
4. Execute the program again and use the `-u` flag followed by the exhentai URL(s) you want to download separated by spaces

Galleries will be saved to `./{LIBRARY_PATH}/sadpanda/`.

For mass downloads place your URLs in the generated `./config/sadpandaurls.txt`.

## New Environment Variables
```TOML
IGNEOUS = ""
IPB_MEMBER_ID = ""
IPB_PASS_HASH = ""
IPB_SESSION_ID = ""
SK = ""
```
Cookies. I did not bother testing which cookies are necessary for exhentai authentication so I simply added all of them.

## Usage

`-h` for help.

`-f` to use URLs stored in `./config/sadpandaurls.txt`

`-u [URL1 URL2 ...]` to use URLs straight from the terminal.

`-c` to enable .webp conversion. Default quality is lossless. Only worth it on original full-resolution images.

`-q QUALITY` to set the desired .webp quality. Recommend 90 for near lossless quality but noticeable size reduction when using. Avoid if the gallery is already compressed to .jpeg.

`--full-resolution` enables full-res download if it is available for the gallery. Some full-res galleries cost GP, so check whether you (need to) have sufficient balance beforehand.

Example:

`sadpandownloader.exe -u https://some.e-hentai.url/ https://or.more.if/you-want -c -q 90`

`sadpandownloader.exe -f -c --full-resolution`

## To-Do

- Add auto-recognition of galleries that can be downloaded at full resolution without GP