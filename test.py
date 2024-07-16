from yt_dlp import YoutubeDL

opts = {
    'extract_flat': 'discard_in_playlist',
    'format_sort': ['ext'],
    'fragment_retries': 10,
    'ignoreerrors': 'only_download',
    'postprocessors': [{'key': 'FFmpegConcat',
                        'only_multi_video': True,
                        'when': 'playlist'}],
    'retries': 10,
    'outtmpl': {'default': f'temp/sex.mp4'}
}
with YoutubeDL(opts) as ydl:
    ydl.download(["https://www.youtube.com/watch?v=81YhiKXsNfE"])