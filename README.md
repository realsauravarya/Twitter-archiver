# Tweet Archiver

This project extracts tweets from a Twitter/X HAR file, saves each tweet as Markdown, downloads associated media, and generates a clean `timeline.md` to browse archived tweets.

## Features

- Parse tweets from `dump.har`
- Save each tweet as:
  - Raw JSON (in `raw/`)
  - Markdown (in `tweets_md/`)
  - Media files (in `media/`)
- Supports photos, GIFs (as mp4), and videos
- Merges `entities.media` and `extended_entities.media`
- Generates a professional, readable `timeline.md`
- Newest-first ordering

## Folder structure

The script writes into `<OUT-DIR>/<USERNAME>/`:

    <OUT-DIR>/
      USERNAME/
        raw/          # Raw tweet JSON files
        tweets_md/    # Markdown snapshots of each tweet
        media/        # Downloaded images, gifs, videos
        timeline.md   # Archive viewer (professional feed)

## Requirements

Install dependencies with pip:

    pip install src/

The minimal required packages are:

    requests
    yt-dlp

Ensure your `.gitignore` excludes HAR files, for example:

    *.har

## Usage

1. Open Twitter/X in your browser.
2. Open Developer Tools → Network tab.
3. Scroll the user timeline you want to archive.
4. Save network traffic as `dump.har` in the project folder.
5. Run the script:

    python main.py --input-har [har-file] --output-dir [out-dir]

The script will parse the HAR, download media, produce Markdown files, and generate `timeline.md`.

## Notes

- Some videos may need cookies or auth; `yt-dlp` can skip protected content.
- VSCode integrated terminal may cause spurious interrupts on Windows. If you see `KeyboardInterrupt`, run the script in a plain terminal (cmd.exe) instead.
- HAR files can contain sensitive data (cookies, tokens). Do not commit them to your repo.

## Optional improvements

Possible future upgrades:

- Thread reconstruction
- Media gallery page
- Search index
- Per-year/month grouping
- Stats dashboard

