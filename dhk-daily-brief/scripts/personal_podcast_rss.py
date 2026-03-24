#!/usr/bin/env python3
"""
Personal Podcast RSS Feed Generator
Watches ~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast
and serves a valid RSS feed that Overcast can subscribe to.

Usage:
    python3 personal_podcast_rss.py

Then subscribe in Overcast to: http://<your-mac-ip>:8765/feed.rss
"""

import argparse
import os
import hashlib
import mimetypes
import socket
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from email.utils import formatdate
import time
from urllib.parse import quote, unquote
from xml.sax.saxutils import escape

from podcast_config import parse_episode_title_from_filename, resolve_audio_dir

PODCAST_DIR: Path | None = None
DEFAULT_PORT = 8765
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
    return quote(name, safe="")

def file_to_pub_date(path):
    """Convert file mtime to RFC 2822 date string."""
    mtime = os.path.getmtime(path)
    return formatdate(mtime, usegmt=True)

def parse_episode_title(filename):
    return parse_episode_title_from_filename(filename)

def generate_rss(base_url):
    """Generate the RSS feed XML."""
    if PODCAST_DIR is None:
        raise RuntimeError("PODCAST_DIR not initialized")
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
      <title>{escape(title)}</title>
      <enclosure url="{url}" length="{size}" type="{mime}"/>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{escape(title)}</description>
      <itunes:duration>0</itunes:duration>
      <itunes:author>{escape(FEED_AUTHOR)}</itunes:author>
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
        port = self.server.server_address[1]
        base_url = f"http://{local_ip}:{port}"

        if self.path == "/feed.rss" or self.path == "/":
            rss = generate_rss(base_url)
            data = rss.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif self.path.startswith("/audio/"):
            filename = unquote(self.path[7:])
            if PODCAST_DIR is None:
                self.send_response(500)
                self.end_headers()
                return
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
                    while True:
                        chunk = f.read(1024 * 256)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def main():
    parser = argparse.ArgumentParser(description="Serve a local RSS feed for your podcast folder")
    parser.add_argument("--audio-dir", default=None, help="Audio directory (overrides config)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to serve on (default: 8765)")
    args = parser.parse_args()

    global PODCAST_DIR
    PODCAST_DIR = resolve_audio_dir(cli_audio_dir=args.audio_dir)

    local_ip = get_local_ip()
    feed_url = f"http://{local_ip}:{args.port}/feed.rss"
    
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

    server = HTTPServer(("0.0.0.0", args.port), FeedHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")


if __name__ == "__main__":
    main()
