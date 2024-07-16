from hashlib import blake2s
from os import path, remove, mkdir, system
from subprocess import run, check_output
from pathlib import Path
from yt_dlp import YoutubeDL

from requests import get

class DownloadFailedException(Exception): pass

def removefiles(*files):
    for file in files:
        remove(file)

def download_url(url:str):
    r = get(url, allow_redirects=True)
    filename = blake2s(url.encode(), digest_size=16).hexdigest()
    filepath = f'temp/{filename}.mp4'
    with open(filepath, 'wb') as file: 
        file.write(r.content)
    return filepath, filename

def downloadyt(url:str):
    hash = blake2s(url.encode(), digest_size=16).hexdigest()
    filename = 'temp/'+hash+'.mp4'

    try:
        with open(filename, 'r'): pass
    except FileNotFoundError: 
        opts = {
            'extract_flat': 'discard_in_playlist',
            'format_sort': ['ext'],
            'fragment_retries': 10,
            'ignoreerrors': 'only_download',
            'postprocessors': [{'key': 'FFmpegConcat',
                                'only_multi_video': True,
                                'when': 'playlist'}],
            'retries': 10,
            'outtmpl': {'default': filename}
        }
        with YoutubeDL(opts) as ydl:
            ydl.download([url])

        return filename, hash
    else: 
        return filename, hash

def convert(input, output):
    run(['./bin/ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', input, '-ac', '1', output], check=True)
    return output

def cut(input, output, duration):
    run(['./bin/ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', input, '-t', str(duration), '-c', 'copy', output])
    return output

def getlenght(path):
    return float(check_output(['./bin/ffprobe', '-hide_banner', '-loglevel', 'error', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path]))

def combine(video, sound, output):
    run(['./bin/ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', video, '-i', sound, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', output])
    return output

def autotune(base, over, output):
    run(['./bin/autotune.exe', '-b', '75', base, over, output], check=True)
    return output

def autotuneyt(basepath:tuple[str, str], overurl):
    try:
        path1, hash1 = basepath
        path2, hash2 = downloadyt(overurl)
    except DownloadFailedException as err:
        raise err

    wav1 = convert(path1, 'temp/'+hash1+'.uncut.wav')
    wav2 = convert(path2, 'temp/'+hash2+'.uncut.wav')

    # cut tracks
    min_duration = min(getlenght(wav1), getlenght(wav2), 30)
    base = cut(wav1, 'temp/'+hash1+'.wav', min_duration)
    over = cut(wav2, 'temp/'+hash2+'.wav', min_duration)
    
    # combine video
    cutvid = cut(path1, 'temp/'+hash1+'.cut.mp4', min_duration)
    hash3 = blake2s((hash1 + hash2).encode(), digest_size=16).hexdigest()
    autotuned = autotune(base, over, 'temp/'+hash3+'.wav')
    video = combine(cutvid, autotuned, 'temp/'+hash3+'.mp4')

    removefiles(path1, path2, wav1, wav2, base, over, cutvid, autotuned)

    return video

def autotune_add_music(videopath:tuple[str, str], musicurl:str, silence=False):
    'Add music instead of autotuning the video'
    try:
        original_video, hash1 = videopath
        music_mp4_path, hash2 = downloadyt(musicurl)
    except DownloadFailedException as err:
        raise err
    hash3 = blake2s((hash1 + hash2 + 'edit').encode(), digest_size=16).hexdigest()
    
    uncut_music = convert(music_mp4_path, 'temp/'+hash2+'.uncut.wav')
    music = cut(uncut_music, 'temp/'+hash2+'.wav', getlenght(original_video))
    video = combine(original_video, music, 'temp/'+hash3+'.mp4')

    removefiles(uncut_music, music, original_video, music_mp4_path)

    return video

try: mkdir('temp')
except: pass
# autotuneyt('https://media.chitter.xyz/media_attachments/files/109/919/153/991/050/303/original/d0ec6787122979ec.mp4', 'https://youtu.be/Kze04Xo0ue0')


# vidpath = autotune_add_music(
#     download_url('https://media.chitter.xyz/media_attachments/files/109/919/153/991/050/303/original/d0ec6787122979ec.mp4'),
#     'https://youtu.be/Kze04Xo0ue0'
# )
# system(f'.\\{vidpath}')