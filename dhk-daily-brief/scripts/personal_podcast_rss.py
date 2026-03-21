#!/usr/bin/env python3
"""
Personal Podcast RSS Feed Generator
Watches ~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast
and serves a valid RSS feed that Overcast can subscribe to.

Usage:
    python3 personal_podcast_rss.py

Then subscribe in Overcast to: http://<your-mac-ip>:8765/feed.rss
"""

import os
import glob
import hashlib
import mimetypes
import socket
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from email.utils import formatdate
import time

PODCAST_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal Podcast"
PORT = 8765
FEED_TITLE = "DHK Personal Podcast"
FEED_DESCRIPTION = "NotebookLM audio overviews — personal reading list"
FEED_AUTHOR = "DHK"

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".mp4", ".wav", ".aac", ".ogg"}

def get_local_ip():
    """Get the Mac's local network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def slugify(name):
    """Make a URL-safe slug from a filename."""
    return name.replace(" ", "%20")

def file_to_pub_date(path):
    """Convert file mtime to RFC 2822 date string."""
    mtime = os.path.getmtime(path)
    return formatdate(mtime, usegmt=True)

def parse_episode_title(filename):
    """
    Turn filenames like '2026-03-21-news.m4a' into readable titles.
    Falls back to the stem if pattern doesn't match.
    """
    stem = Path(filename).stem
    parts = stem.split("-")
    
    # Try to parse YYYY-MM-DD-category pattern
    if len(parts) >= 4:
        try:
            date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
            date = datetime.strptime(date_str, "%Y-%m-%d")
            category = " ".join(parts[3:]).title()
            category_emoji = {
                "news": "📰 News & Current Affairs",
                "think": "🧠 Things to Think About", 
                "professional": "💼 Professional Reading",
            }.get(parts[3].lower(), category)
            return f"{category_emoji} — {date.strftime('%b %d, %Y')}"
        except ValueError:
            pass
    
    return stem.replace("-", " ").replace("_", " ").title()

def generate_rss(base_url):
    """Generate the RSS feed XML."""
    files = []
    for ext in AUDIO_EXTENSIONS:
        files.extend(PODCAST_DIR.glob(f"*{ext}"))
        files.extend(PODCAST_DIR.glob(f"*{ext.upper()}"))
    
    # Sort newest first
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    
    items = []
    for f in files:
        filename = f.name
        title = parse_episode_title(filename)
        pub_date = file_to_pub_date(f)
        size = os.path.getsize(f)
        mime = mimetypes.guess_type(filename)[0] or "audio/mpeg"
        url = f"{base_url}/audio/{slugify(filename)}"
        guid = hashlib.md5(filename.encode()).hexdigest()
        
        items.append(f"""
    <item>
      <title>{title}</title>
      <enclosure url="{url}" length="{size}" type="{mime}"/>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{title}</description>
      <itunes:duration>0</itunes:duration>
      <itunes:author>{FEED_AUTHOR}</itunes:author>
    </item>""")
    
    now = formatdate(usegmt=True)
    items_xml = "".join(items)
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{FEED_TITLE}</title>
    <description>{FEED_DESCRIPTION}</description>
    <link>{base_url}</link>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <itunes:author>{FEED_AUTHOR}</itunes:author>
    <itunes:explicit>no</itunes:explicit>
    <itunes:category text="Technology"/>
    {items_xml}
  </channel>
</rss>"""


class FeedHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging; print cleaner output
        print(f"  → {self.command} {self.path}")

    def do_GET(self):
        local_ip = get_local_ip()
        base_url = f"http://{local_ip}:{PORT}"

        if self.path == "/feed.rss" or self.path == "/":
            rss = generate_rss(base_url)
            data = rss.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif self.path.startswith("/audio/"):
            filename = self.path[7:].replace("%20", " ")
            filepath = PODCAST_DIR / filename
            if filepath.exists() and filepath.suffix.lower() in AUDIO_EXTENSIONS:
                size = os.path.getsize(filepath)
                mime = mimetypes.guess_type(filename)[0] or "audio/mpeg"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def main():
    local_ip = get_local_ip()
    feed_url = f"http://{local_ip}:{PORT}/feed.rss"
    
    if not PODCAST_DIR.exists():
        print(f"⚠️  Podcast folder not found: {PODCAST_DIR}")
        print("   Create it first with:")
        print(f"   mkdir -p '{PODCAST_DIR}'")
        return

    # Count audio files
    files = []
    for ext in AUDIO_EXTENSIONS:
        files.extend(PODCAST_DIR.glob(f"*{ext}"))
    
    print(f"""
╔════════════════════════════════════════════════╗
║       DHK Personal Podcast RSS Server          ║
╚════════════════════════════════════════════════╝

📁 Folder:  {PODCAST_DIR}
🎧 Episodes: {len(files)} audio file(s) found
🌐 Feed URL: {feed_url}

Subscribe in Overcast:
  1. Open Overcast → + → Add URL
  2. Paste: {feed_url}

Keep this terminal window open while listening.
Press Ctrl+C to stop.

─────────────────────────────────────────────────
""")

    server = HTTPServer(("0.0.0.0", PORT), FeedHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")


if __name__ == "__main__":
    main()
