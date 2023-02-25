from hashlib import blake2s
from os import path, remove, mkdir
from subprocess import run, check_output
from pytube import YouTube
from pytube.exceptions import RegexMatchError
from pathlib import Path

from requests import get

class DownloadFailedException(Exception): pass

def removefiles(*files):
    for file in files:
        remove(file)

def exists(url):
    'check if there is a visible video url'
    try: 
        video = YouTube(url)
        return True
    except RegexMatchError: 
        return False

def download_url(url:str):
    r = get(url, allow_redirects=True)
    filename = blake2s(url.encode(), digest_size=16).hexdigest()
    filepath = f'temp/{filename}.mp4'
    with open(filepath, 'wb') as file: 
        file.write(r.content)
    return filepath, filename

def downloadyt(url:str):
    hash = blake2s(url.encode(), digest_size=16).hexdigest()

    try:
        with open('temp/'+hash+'.mp4', 'r'): pass
    except FileNotFoundError: 
        video = YouTube(url).streams.filter(progressive=True, file_extension='mp4')\
            .order_by('resolution') \
            .asc()                  \
            .first()                \
        
        if video:
            return video.download('temp/', hash+'.mp4'), hash

    else: 
        return 'temp/'+hash+'.mp4', hash
    raise Exception

def convert(input, output):
    run(['./bin/ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', input, '-ac', '1', output], check=True)
    return output

def cut(input, output, duration):
    run(['./bin/ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', input, '-t', str(duration), '-c', 'copy', output])
    return output

def getlenght(path):
    return float(check_output(['./bin/ffprobe', '-hide_banner', '-loglevel', 'error', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path]))

def combine(video, sound, output):
    run(['./bin/ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', video, '-i', sound, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', output])
    return output

def autotune(base, over, output):
    run(['./bin/autotune.exe', '-b', '75', base, over, output], check=True)
    return output

def autotuneyt(baselink, overurl):
    try:
        path1, hash1 = download_url(baselink)
        path2, hash2 = downloadyt(overurl)
    except DownloadFailedException:
        return

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

try: mkdir('temp')
except: pass
# autotuneyt('https://media.chitter.xyz/media_attachments/files/109/919/153/991/050/303/original/d0ec6787122979ec.mp4', 'https://youtu.be/Kze04Xo0ue0')