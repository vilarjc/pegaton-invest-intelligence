#!/usr/bin/env python3
"""
============================================================================
YOUTUBE TRANSCRIPT EXTRACTOR
============================================================================
Extracts transcripts from YouTube videos using Tor proxy to bypass IP blocks.
Works from cloud/server IPs where YouTube normally blocks requests.

Usage:
    python youtube_transcript.py https://www.youtube.com/watch?v=VIDEO_ID
    python youtube_transcript.py https://youtu.be/VIDEO_ID
    python youtube_transcript.py VIDEO_ID
============================================================================
"""

import sys
import re
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def extract_video_id(url_or_id: str) -> str:
    """Extract YouTube video ID from various URL formats or raw ID."""
    # Already just an ID (11 chars, alphanumeric + _ - )
    if re.match(r'^[A-Za-z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # youtu.be/ID
    match = re.search(r'youtu\.be/([A-Za-z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)
    
    # youtube.com/watch?v=ID
    match = re.search(r'youtube\.com/watch\?.*v=([A-Za-z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)
    
    # youtube.com/embed/ID
    match = re.search(r'youtube\.com/embed/([A-Za-z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)
    
    # youtube.com/shorts/ID
    match = re.search(r'youtube\.com/shorts/([A-Za-z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)
    
    raise ValueError(f"Could not extract video ID from: {url_or_id}")


def get_transcript(video_id: str, languages=('es', 'en'), preserve_formatting=True) -> list[dict]:
    """
    Fetch YouTube transcript using Tor proxy.
    
    Args:
        video_id: YouTube video ID
        languages: Preferred language codes (tries in order)
        preserve_formatting: Keep line breaks in auto-generated subs
    
    Returns:
        List of dicts with 'text', 'start' (seconds), 'duration' (seconds)
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import GenericProxyConfig
    
    proxy = GenericProxyConfig(
        http_url='socks5://127.0.0.1:9050',
        https_url='socks5://127.0.0.1:9050'
    )
    api = YouTubeTranscriptApi(proxy_config=proxy)
    
    return list(api.fetch(video_id, languages=languages, preserve_formatting=preserve_formatting))


def transcript_to_text(segments: list[dict]) -> str:
    """Convert transcript segments to plain text."""
    lines = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            lines.append(text)
    return ' '.join(lines)


def format_timestamp(seconds: float) -> str:
    """Format seconds to MM:SS or H:MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def transcript_to_timestamped(segments: list[dict]) -> str:
    """Convert transcript segments to timestamped text."""
    lines = []
    for seg in segments:
        ts = format_timestamp(seg.start)
        text = seg.text.strip()
        if text:
            lines.append(f"[{ts}] {text}")
    return '\n'.join(lines)


def get_video_title(video_id: str) -> str:
    """Get video title via oEmbed API (no proxy needed, lightweight)."""
    import urllib.request
    import json
    
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        with urllib.request.urlopen(oembed_url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get('title', 'Unknown'), data.get('author_name', 'Unknown')
    except Exception:
        return 'Unknown', 'Unknown'


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_transcript.py <URL_or_ID>")
        sys.exit(1)
    
    video_id = extract_video_id(sys.argv[1])
    
    print(f"🎬 Fetching transcript for: {video_id}")
    print(f"   URL: https://www.youtube.com/watch?v={video_id}")
    print()
    
    try:
        # Get video info via oEmbed (no proxy needed)
        title, channel = get_video_title(video_id)
        print(f"📺 {title}")
        print(f"👤 {channel}")
        print()
        
        # Get transcript (try Spanish first, then English)
        try:
            segments = get_transcript(video_id, languages=('es', 'en'))
            lang = "español"
        except Exception:
            segments = get_transcript(video_id, languages=('en',))
            lang = "inglés"
        
        print(f"📝 Transcripción ({lang}): {len(segments)} segmentos")
        print()
        
        # Print with timestamps
        print(transcript_to_timestamped(segments))
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
