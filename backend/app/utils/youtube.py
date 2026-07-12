import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# Intercept requests.Session initialization globally to inject a modern browser User-Agent.
# This prevents YouTube from instantly blocking timedtext requests with a "python-requests" User-Agent.
original_init = requests.Session.__init__
def new_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    self.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.youtube.com/",
    })
requests.Session.__init__ = new_init

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
    Returns None if subtitles are disabled, video is private, or an error occurs.
    """
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([item['text'] for item in transcript_list])
        return transcript_text
    except Exception as e:
        print(f"Error fetching YouTube transcript for {video_id}: {e}")
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
