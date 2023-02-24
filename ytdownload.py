from pytube import YouTube
from pytube.exceptions import RegexMatchError

try: video = YouTube('link')
except RegexMatchError: return False

