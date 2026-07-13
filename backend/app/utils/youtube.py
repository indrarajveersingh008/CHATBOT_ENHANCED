import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi

from urllib.parse import urlparse, parse_qs

def extract_youtube_video_id(text: str) -> str | None:
    """
    Extracts the 11-character YouTube video ID from a text string.
    Returns None if no YouTube link is found.
    Handles standard watch URLs, shorts, embed, live, youtu.be, and query parameters in any order.
    """
    if not text:
        return None
    
    # Locate potential YouTube URLs in the input text
    url_pattern = r'(https?://[^\s]+|www\.[^\s]+|youtube\.com/[^\s]+|youtu\.be/[^\s]+)'
    matches = re.findall(url_pattern, text)
    
    for url in matches:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            
        try:
            u_pars = urlparse(url)
            netloc = u_pars.netloc.lower()
            path = u_pars.path
            
            # Handle youtu.be domain
            if 'youtu.be' in netloc:
                v_id = path.lstrip('/')
                if len(v_id) >= 11:
                    return v_id[:11]
            
            # Handle youtube.com and youtube-nocookie.com domains
            if 'youtube.com' in netloc or 'youtube-nocookie.com' in netloc:
                # Query param check
                query_params = parse_qs(u_pars.query)
                if 'v' in query_params:
                    v_id = query_params['v'][0]
                    if len(v_id) == 11:
                        return v_id
                
                # Path segment check for: /embed/ID, /v/ID, /shorts/ID, /live/ID
                parts = [p for p in path.split('/') if p]
                for keyword in ['embed', 'v', 'shorts', 'live']:
                    if keyword in parts:
                        idx = parts.index(keyword)
                        if idx + 1 < len(parts):
                            v_id = parts[idx + 1]
                            v_id = v_id.split('?')[0]
                            if len(v_id) >= 11:
                                return v_id[:11]
                                
        except Exception:
            pass
            
    # Fallback to regex pattern search
    fallback_pattern = r'(?:youtube(?:-nocookie)?\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?|shorts|live)/|.*[?&]v=)|youtu\.be/)(?P<id>[a-zA-Z0-9_-]{11})'
    match = re.search(fallback_pattern, text)
    if match:
        return match.group("id")
        
    return None

def get_youtube_metadata(video_id: str) -> dict | None:
    """
    Scrapes the YouTube watch page to retrieve the video's Title and Description
    from OpenGraph meta tags.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.youtube.com/",
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            html = res.text
            title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            title = title_match.group(1) if title_match else None
            
            desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
            desc = desc_match.group(1) if desc_match else None
            
            if not title:
                title_match = re.search(r'<title>([^<]+)</title>', html)
                if title_match:
                    title = title_match.group(1).replace(" - YouTube", "")
            
            import html as html_parser
            if title:
                title = html_parser.unescape(title)
            if desc:
                desc = html_parser.unescape(desc)
                
            return {
                "title": title,
                "description": desc
            }
    except Exception as e:
        print(f"Error fetching YouTube metadata for {video_id}: {e}")
    return None

def get_youtube_transcript(video_id: str) -> str | None:
    """
    Fetches the transcript for a given YouTube video ID.
    Supports local scraper with auto-fallback to a public web API
    if local scraping is blocked (common on cloud/serverless hosts).
    Returns None if subtitles are disabled, video is private, or an error occurs.
    """
    # Tier 1: Local scraping using youtube-transcript-api (preferred for speed/local run)
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.youtube.com/",
        })
        
        api = YouTubeTranscriptApi(http_client=session)
        
        try:
            transcript_list = api.fetch(video_id, languages=["en"])
        except Exception:
            transcripts = api.list(video_id)
            first_transcript = next(iter(transcripts))
            transcript_list = first_transcript.fetch()
            
        transcript_text = " ".join([item.text for item in transcript_list])
        if transcript_text:
            return transcript_text
            
    except Exception as e:
        print(f"Local YouTube transcript scraping failed/blocked for {video_id}: {e}")
        
    # Tier 2: Fallback to public YouTube transcript web API (bypasses cloud IP blocks)
    try:
        print(f"Attempting fallback timedtext API query for video {video_id}...")
        url = f"https://youtube-transcript.ai/transcript/{video_id}.txt"
        res = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }, timeout=10)
        
        if res.status_code == 200 and res.text:
            # Check if it returned a transcript or some error text
            if "Transcript:" in res.text or len(res.text) > 100:
                return res.text
            
    except Exception as e:
        print(f"Fallback YouTube API query failed for {video_id}: {e}")
        
    return None

def get_youtube_context(message: str) -> str | None:
    """
    Detects if a message contains a YouTube link, fetches the transcript and metadata,
    and returns a formatted context string.
    Returns None if no link is detected.
    """
    video_id = extract_youtube_video_id(message)
    if not video_id:
        return None
        
    metadata = get_youtube_metadata(video_id)
    transcript = get_youtube_transcript(video_id)
    
    title = metadata.get("title") if metadata else None
    desc = metadata.get("description") if metadata else None
    
    if transcript:
        context_parts = [
            f"--- YOUTUBE VIDEO CONTEXT (ID: {video_id}) ---"
        ]
        if title:
            context_parts.append(f"Title: {title}")
        if desc:
            context_parts.append(f"Description: {desc}")
            
        context_parts.extend([
            "\nTranscript:",
            transcript,
            "----------------------------------------------"
        ])
        return "\n".join(context_parts)
    elif title:
        return (
            f"--- YOUTUBE VIDEO CONTEXT (ID: {video_id}) ---\n"
            f"Title: {title}\n"
            f"Description: {desc or 'No description available.'}\n\n"
            f"[System Notice: The full transcript/subtitles could not be fetched for this video (they might be disabled or unavailable). "
            f"Use the title and description above to help the user. Politely explain that you couldn't access the full transcript, "
            f"but address their request as best as you can using the video title and description details.]\n"
            f"----------------------------------------------"
        )
    else:
        return (
            f"--- YOUTUBE VIDEO CONTEXT (ID: {video_id}) ---\n"
            f"[System Notice: The user shared a YouTube link to this video, but neither the transcript nor video details could be fetched. "
            f"Please politely inform the user that subtitles/transcripts are disabled, unavailable, or the video is private/inaccessible.]\n"
            f"----------------------------------------------"
        )
