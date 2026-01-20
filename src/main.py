import scrape_tweets as st
import os
import argparse


def main():
    print("Hello from twitter-archiver!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse the tweets from this page load's HAR file."
    )
    parser.add_argument(
        "--input-har", type=str, help="Path to HAR file to be processed."
    )
    parser.add_argument(
        "--output-dir",
        default="./archive",
        type=str,
        help="The folder to store output.",
    )
    parser.add_argument(
        "--username",
        default="anonymous",
        type=str,
        help="Username to associate to the extracted data.",
    )
    args = parser.parse_args()

    ROOT = os.path.join(args.output_dir, args.username)
    OUT = os.path.join(ROOT, "tweets_md")
    MEDIA_ROOT = os.path.join(ROOT, "media")
    RAW = os.path.join(ROOT, "raw")

    for p in [ROOT, OUT, MEDIA_ROOT, RAW]:
        os.makedirs(p, exist_ok=True)

    print("\nLoading HAR file...")
    blobs = st.load_blobs_from_har(args.input_har)

    all_tweets = []
    for blob in blobs:
        all_tweets.extend(st.extract_from_blob(blob))

    seen = set()
    uniq = []
    for t in all_tweets:
        if t["id"] not in seen:
            seen.add(t["id"])
            uniq.append(t)

    print(f"Found {len(uniq)} unique tweets\n")

    for tw in uniq:
        st.save_tweet_md(RAW, OUT, MEDIA_ROOT, tw)

    st.generate_timeline(args.username, ROOT, OUT, MEDIA_ROOT)

    print("\nDONE\n")
