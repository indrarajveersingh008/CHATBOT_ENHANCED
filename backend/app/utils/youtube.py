import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# Regular expression to extract YouTube Video ID from various link formats
YOUTUBE_REGEX = r'(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed/|v/|shorts/|e/|[^/\s]+/)*(?P<id>[a-zA-Z0-9_-]{11})'

def extract_youtube_video_id(text: str) -> str | None:
    """
    Extracts the 11-character YouTube video ID from a text string.
    Returns None if no YouTube link is found.
    """
    if not text:
        return None
    match = re.search(YOUTUBE_REGEX, text)
    if match:
        return match.group("id")
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
    Detects if a message contains a YouTube link, fetches the transcript,
    and returns a formatted context string.
    Returns None if no link is detected.
    """
    video_id = extract_youtube_video_id(message)
    if not video_id:
        return None
        
    transcript = get_youtube_transcript(video_id)
    if transcript:
        return (
            f"--- YOUTUBE VIDEO TRANSCRIPT (ID: {video_id}) ---\n"
            f"The user has shared a YouTube link to this video. Use this transcript content to summarize, "
            f"answer questions, or reference what was said in the video:\n"
            f"{transcript}\n"
            f"------------------------------------------------"
        )
    else:
        return (
            f"--- YOUTUBE VIDEO CONTEXT (ID: {video_id}) ---\n"
            f"[System Notice: The user shared a YouTube link to this video, but the transcript could not be fetched. "
            f"Please politely inform the user that subtitles/transcripts are disabled, unavailable, or the video is private/inaccessible.]\n"
            f"----------------------------------------------"
        )
