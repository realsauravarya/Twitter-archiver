import os
import json
import subprocess
import requests
import time
from urllib.parse import urlparse
from datetime import datetime


# ===========================
# CONFIG
# ===========================



# ===========================
# MEDIA DOWNLOAD
# ===========================

def pick_best_mp4(variants):
    mp4s = [
        v for v in variants
        if v.get("content_type") == "video/mp4" and v.get("bitrate") is not None
    ]
    if not mp4s:
        return None
    return sorted(mp4s, key=lambda x: x["bitrate"], reverse=True)[0]["url"]


def download_image(url, folder):
    filename = os.path.basename(urlparse(url).path)
    if not filename:
        filename = f"img_{int(datetime.now().timestamp())}.jpg"

    file = os.path.join(folder, filename)
    if os.path.exists(file):
        return file

    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            with open(file, "wb") as f:
                f.write(r.content)
            return file
    except:
        return None


def download_video(url, folder, name):
    out = os.path.join(folder, f"{name}.mp4")

    if os.path.exists(out):
        return out

    try:
        subprocess.run(
            [
                "yt-dlp",
                "--no-warnings",
                "--quiet",
                "--no-progress",
                "--ignore-errors",
                "--socket-timeout", "10",
                "--retries", "2",
                "-o", out,
                url
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=25
        )
    except subprocess.TimeoutExpired:
        print(f"[WARN] yt-dlp timeout for: {url}")
        return None
    except Exception as e:
        print(f"[ERR] yt-dlp failed for {url}: {e}")
        return None

    return out if os.path.exists(out) else None


# ===========================
# SAVE MEDIA + MD
# ===========================

def save_media(MEDIA_ROOT, tweet):
    media = tweet.get("media", [])
    if not media:
        return None

    tid = tweet["id"]
    folder = os.path.join(MEDIA_ROOT, tid)
    os.makedirs(folder, exist_ok=True)

    md = ""

    for m in media:
        t = m.get("type")

        # PHOTO
        if t == "photo":
            url = m.get("media_url_https")
            if url:
                local = download_image(url, folder)
                if local:
                    rel = f"../media/{tid}/{os.path.basename(local)}"
                    md += f"![image]({rel})\n"
            continue

        # GIF + VIDEO
        if t in ["video", "animated_gif"]:
            variants = m.get("video_info", {}).get("variants", [])
            best = pick_best_mp4(variants)

            if best:
                name = tid if t == "video" else f"{tid}_gif"
                local = download_video(best, folder, name)

                if local:
                    rel = f"../media/{tid}/{os.path.basename(local)}"
                    md += f'<video controls src="{rel}" style="max-width:100%;"></video>\n'
            continue

        # FALLBACK
        url = m.get("media_url_https") or m.get("url")
        if url:
            local = download_image(url, folder)
            if local:
                rel = f"../media/{tid}/{os.path.basename(local)}"
                md += f"![media]({rel})\n"

    return md or None


# ===========================
# SAVE TWEET MD (RAW ALWAYS SAVED)
# ===========================

def save_tweet_md(RAW, OUT, MEDIA_ROOT, tweet):
    tid = tweet["id"]

    # Always save RAW JSON
    raw_path = os.path.join(RAW, f"{tid}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(tweet, f, indent=2)

    # Build MD filename
    raw_time = tweet.get("createdAt", "")
    safe_timestamp = "unknown"

    try:
        dt = datetime.strptime(raw_time, "%a %b %d %H:%M:%S %z %Y")
        safe_timestamp = dt.strftime("%Y%m%d_%H%M%S")
    except:
        print(raw_time)
        pass

    filename = f"{safe_timestamp}_{tid}.md"
    md_file = os.path.join(OUT, filename)

    # Only skip MD writing, not raw
    if os.path.exists(md_file):
        return

    text = tweet.get("text", "")
    created = tweet.get("createdAt", "")
    url = tweet.get("url", "")
    media_md = save_media(MEDIA_ROOT, tweet) or "No media"

    md = f"""# Tweet {tid}

**Date:** {created}  
**URL:** {url}

---

## Text

{text}

---

## Media

{media_md}

---

"""

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md)

    print("Saved:", md_file)


# ===========================
# TWEET PARSER
# ===========================

def parse_tweet_result(result):
    tid = result.get("rest_id")
    if not tid:
        return None

    legacy = result.get("legacy", {})

    tweet = {
        "id": tid,
        "text": legacy.get("full_text") or legacy.get("text", ""),
        "createdAt": legacy.get("created_at", ""),
        "url": f"https://x.com/i/web/status/{tid}",
        "media": []
    }

    # Merge media arrays
    ent1 = legacy.get("entities", {}).get("media", [])
    ent2 = legacy.get("extended_entities", {}).get("media", [])
    merged = {m.get("id_str"): m for m in ent1 + ent2 if isinstance(m, dict)}
    tweet["media"] = list(merged.values())

    return tweet


# ===========================
# RECURSIVE EXTRACTION
# ===========================

def collect_tweets_recursively(obj, out):
    if isinstance(obj, dict):

        if obj.get("__typename") == "Tweet":
            t = parse_tweet_result(obj)
            if t:
                out.append(t)

        if obj.get("__typename") == "TweetWithVisibilityResults":
            inner = obj.get("tweet", {})
            t = parse_tweet_result(inner)
            if t:
                out.append(t)

        for v in obj.values():
            collect_tweets_recursively(v, out)

    elif isinstance(obj, list):
        for v in obj:
            collect_tweets_recursively(v, out)


def extract_from_blob(blob):
    tweets = []
    collect_tweets_recursively(blob, tweets)
    return tweets


# ===========================
# LOAD HAR
# ===========================

def load_blobs_from_har(file):
    with open(file, "r", encoding="utf-8") as f:
        har = json.load(f)

    blobs = []

    for entry in har.get("log", {}).get("entries", []):
        content = entry.get("response", {}).get("content", {})
        mime = content.get("mimeType", "")
        text = content.get("text")

        if not text or "json" not in mime.lower():
            continue

        try:
            js = json.loads(text)
        except:
            continue

        if '"tweet_results"' not in text:
            continue

        blobs.append(js)

    print(f"Loaded {len(blobs)} blobs containing tweet data from HAR")
    return blobs


# ===========================
# TIMELINE GENERATOR (PROFESSIONAL FEED)
# ===========================

def generate_timeline(USERNAME, ROOT, OUT, MEDIA_ROOT, RAW):
    TIMELINE = os.path.join(ROOT, "timeline.md")
    print("\nGenerating timeline...")

    entries = []

    for fname in os.listdir(OUT):
        if not fname.endswith(".md"):
            continue

        parts = fname.split("_")
        if len(parts) < 3:
            continue

        timestamp = f"{parts[0]}_{parts[1]}"
        tid = parts[2].replace(".md", "")

        # extract preview
        preview = ""
        with open(os.path.join(OUT, fname), "r", encoding="utf-8") as f:
            for line in f:
                if (
                    line.strip()
                    and not line.startswith("#")
                    and not line.startswith("**")
                    and not line.startswith("---")
                ):
                    preview = line.strip()
                    break

        if len(preview) > 180:
            preview = preview[:180] + "…"

        # thumbnail
        thumb = ""
        media_dir = os.path.join(MEDIA_ROOT, tid)
        if os.path.isdir(media_dir):
            for file in os.listdir(media_dir):
                if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    thumb = f"![thumb](media/{tid}/{file})" 
                    break

        entries.append((timestamp, tid, fname, preview, thumb))

    entries.sort(reverse=True)

    with open(TIMELINE, "w", encoding="utf-8") as f:
        f.write(f"# 🗂️ @{USERNAME} Tweet Archive\n")

        for ts, tid, fname, preview, thumb in entries:
            human = (
                f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} "
                f"{ts[9:11]}:{ts[11:13]}:{ts[13:15]}"
            )

            f.write(f"## 🗂️ {human} — Tweet {tid}\n\n")

            if preview:
                f.write(f"> **Text:** {preview}\n>\n")

            if thumb:
                f.write(f"> 🖼️ {thumb}\n>\n")

            f.write(f"> 🔗 **Open full tweet:** [View Markdown](tweets_md/{fname})\n\n")
            f.write("---\n\n")

    print("Timeline generated at:", TIMELINE)
