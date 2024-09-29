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

`-q QUALITY` to enable .webp conversion and set the desired quality. Recommend 90 for near lossless quality but noticeable size reduction.

Example:

`sadpandownloader.exe -f -q 90`

## To-Do

- Add option to download low-res images without GP.