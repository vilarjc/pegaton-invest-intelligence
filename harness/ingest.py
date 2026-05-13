#!/usr/bin/env python3
"""
============================================================================
INGEST — Universal Input Handlers
============================================================================
Detects input type and extracts structured content from any source:
  - YouTube URLs → transcript via Tor proxy
  - File paths → file contents
  - Plain text → as-is
  - URLs → web content
  - Agent conversations → structured summary

Usage:
    from harness.ingest import ingest
    result = ingest("https://youtu.be/VIDEO_ID")
    result = ingest("/path/to/file.md")
    result = ingest("User said: hello world")
============================================================================
"""

import os
import re
import sys
import json
from typing import Optional


def detect_input_type(text: str) -> str:
    """
    Detect what kind of input this is.
    
    Returns one of: 'youtube', 'file', 'url', 'json', 'text'
    """
    text = text.strip()
    
    # YouTube URL
    youtube_patterns = [
        r'youtube\.com/watch\?.*v=([A-Za-z0-9_-]{11})',
        r'youtu\.be/([A-Za-z0-9_-]{11})',
        r'youtube\.com/embed/([A-Za-z0-9_-]{11})',
        r'youtube\.com/shorts/([A-Za-z0-9_-]{11})',
    ]
    for pattern in youtube_patterns:
        if re.search(pattern, text):
            return 'youtube'
    
    # Raw video ID (11 alphanumeric chars)
    if re.match(r'^[A-Za-z0-9_-]{11}$', text):
        return 'youtube'
    
    # File path
    if text.startswith('/') or text.startswith('./') or text.startswith('../') or text.startswith('~/'):
        if os.path.isfile(os.path.expanduser(text)):
            return 'file'
    
    # Generic URL
    if text.startswith('http://') or text.startswith('https://'):
        return 'url'
    
    # JSON string
    if text.startswith('{') or text.startswith('['):
        try:
            json.loads(text)
            return 'json'
        except json.JSONDecodeError:
            pass
    
    # Default: plain text
    return 'text'


def extract_youtube_video_id(text: str) -> Optional[str]:
    """Extract YouTube video ID from any URL format or raw ID."""
    text = text.strip()
    
    # Raw ID
    if re.match(r'^[A-Za-z0-9_-]{11}$', text):
        return text
    
    patterns = [
        r'youtu\.be/([A-Za-z0-9_-]{11})',
        r'youtube\.com/watch\?.*v=([A-Za-z0-9_-]{11})',
        r'youtube\.com/embed/([A-Za-z0-9_-]{11})',
        r'youtube\.com/shorts/([A-Za-z0-9_-]{11})',
        r'youtube\.com/v/([A-Za-z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None


def fetch_youtube_transcript(video_id: str) -> dict:
    """
    Fetch YouTube transcript via Tor proxy.
    Returns dict with title, channel, segments, full_text.
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import GenericProxyConfig
    
    # Try Spanish first, then English
    languages_to_try = [('es', 'en'), ('en',)]
    segments = None
    lang_used = 'unknown'
    
    for langs in languages_to_try:
        try:
            proxy = GenericProxyConfig(
                http_url='socks5://127.0.0.1:9050',
                https_url='socks5://127.0.0.1:9050'
            )
            api = YouTubeTranscriptApi(proxy_config=proxy)
            result = api.fetch(video_id, languages=list(langs))
            segments = [{'text': s.text, 'start': s.start, 'duration': s.duration} for s in result]
            lang_used = langs[0]
            break
        except Exception:
            continue
    
    if not segments:
        raise RuntimeError(f"Could not fetch transcript for video {video_id}")
    
    # Get title via oEmbed
    import urllib.request
    title = 'Unknown'
    channel = 'Unknown'
    try:
        oembed = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with urllib.request.urlopen(oembed, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            title = data.get('title', 'Unknown')
            channel = data.get('author_name', 'Unknown')
    except Exception:
        pass
    
    full_text = ' '.join(s['text'] for s in segments)
    
    return {
        'video_id': video_id,
        'title': title,
        'channel': channel,
        'language': lang_used,
        'segment_count': len(segments),
        'segments': segments,
        'full_text': full_text,
        'url': f"https://www.youtube.com/watch?v={video_id}",
    }


def read_file(path: str) -> dict:
    """Read a file and return its contents."""
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    return {
        'path': path,
        'filename': os.path.basename(path),
        'extension': os.path.splitext(path)[1],
        'size_bytes': os.path.getsize(path),
        'content': content,
    }


def fetch_url(url: str, timeout: int = 15) -> dict:
    """Fetch content from a URL."""
    import urllib.request
    
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = resp.read().decode('utf-8', errors='replace')
    
    return {
        'url': url,
        'status': resp.status,
        'content_type': resp.headers.get('Content-Type', ''),
        'content': content,
    }


def ingest(text: str, input_type: Optional[str] = None) -> dict:
    """
    Universal ingest function.
    
    Args:
        text: The input (URL, file path, raw text, etc.)
        input_type: Optional override for input type detection
    
    Returns:
        dict with 'type', 'content', 'metadata', 'raw'
    """
    if input_type is None:
        input_type = detect_input_type(text)
    
    result = {
        'type': input_type,
        'raw': text,
        'content': '',
        'metadata': {},
    }
    
    if input_type == 'youtube':
        video_id = extract_youtube_video_id(text)
        if not video_id:
            raise ValueError(f"Could not extract YouTube video ID from: {text}")
        data = fetch_youtube_transcript(video_id)
        result['content'] = data['full_text']
        result['metadata'] = {
            'video_id': data['video_id'],
            'title': data['title'],
            'channel': data['channel'],
            'language': data['language'],
            'segment_count': data['segment_count'],
            'source_url': data['url'],
        }
        # Also include timestamped version
        result['timestamped_text'] = '\n'.join(
            f"{_fmt_ts(s['start'])} {s['text']}" for s in data['segments']
        )
    
    elif input_type == 'file':
        data = read_file(text)
        result['content'] = data['content']
        result['metadata'] = {
            'path': data['path'],
            'filename': data['filename'],
            'extension': data['extension'],
            'size_bytes': data['size_bytes'],
        }
    
    elif input_type == 'url':
        data = fetch_url(text)
        result['content'] = data['content']
        result['metadata'] = {
            'url': data['url'],
            'content_type': data['content_type'],
        }
    
    elif input_type == 'json':
        result['content'] = text
        result['metadata'] = {'parsed': True}
    
    else:  # plain text
        result['content'] = text
        result['metadata'] = {'char_count': len(text), 'word_count': len(text.split())}
    
    return result


def _fmt_ts(seconds: float) -> str:
    """Format seconds to MM:SS or H:MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <input>")
        print("Detects type automatically. Supports: YouTube URLs, file paths, URLs, text.")
        sys.exit(1)
    
    result = ingest(sys.argv[1])
    print(json.dumps({
        'type': result['type'],
        'metadata': result['metadata'],
        'content_preview': result['content'][:300] + '...' if len(result['content']) > 300 else result['content'],
    }, ensure_ascii=False, indent=2))
