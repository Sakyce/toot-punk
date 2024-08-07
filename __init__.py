from abc import ABC
from mastodon import Mastodon
from bs4 import BeautifulSoup
import webbrowser, tempfile, json
from mastodon.errors import MastodonNotFoundError, MastodonAPIError
from time import sleep, time
from hashlib import blake2s

from requests import get
import vocoder

with open('credential.secret', 'r') as file:creds = file.readlines() # client id, client secret, access token
client = Mastodon(
    api_base_url='https://botsin.space',
    client_id=creds[0],
    client_secret=creds[1],
    access_token=creds[2],
    )

def isPublic(status):
    return 'Also, *please set your autotune request in UNLISTED*!' if status['visibility'] == 'public' else ''

class BaseRequest(ABC):
    def treat(self):
        pass

    def destroy(self):
        requests_schedule.remove(self)
        
class BadRequest(BaseRequest):
    def __init__(self, text, status_to_reply) -> None:
        self.text = text
        self.status_to_reply = status_to_reply
    
    def treat(self):
        ping = f"@{self.status_to_reply['account']['acct']}"
        # public_reaction = 'Also, *please set your autotune request in UNLISTED*!' if self.status_to_reply.status['visibility'] == 'public' else ''
        client.status_post(' '.join([ping,  self.text]), visibility='unlisted', in_reply_to_id=self.status_to_reply.status)

requests_schedule:list[BaseRequest] = []

def getfiledata(filename): # 109921593256401643
    file_data = None
    with open(filename, 'rb') as file:
        file_data = file.read()
    return file_data

def upload_video(video_path:str, original_status, notification, message:str):
    media_post = client.media_post(getfiledata(video_path), 'video/mp4')
    print('uploading to mastodon')
    sleep(10)
    try: 
        status = client.status_post(
            message, 
            media_ids=media_post['id'], 
            sensitive=original_status['sensitive'],
            in_reply_to_id=notification.status,
            spoiler_text=original_status['spoiler_text'],
            visibility='unlisted' if original_status['sensitive'] else 'public'
                )
        sleep(2)
        if not original_status['sensitive']:
            client.status_reblog(status['id'])
    except MastodonNotFoundError: # the request may have been deleted meanwhile
        return

class AutotuneRequest(BaseRequest):
    toot_video_path:tuple[str, str]
    youtube_url:str
    
    def __init__(self, toot_video:tuple[str, str], youtube_url:str, notification, video_status) -> None:
        self.toot_video = toot_video
        self.youtube_url = youtube_url
        self.notification = notification
        self.video_status = video_status
    
    def treat(self):
        try:
            newvid = vocoder.autotuneyt(self.toot_video, self.youtube_url)
        except Exception as err: 
            print(err)
            requests_schedule.append(BadRequest(f'I couldn\'t treat your request, please report this issue on Github. ({str(err)})', self.notification))
        else:
            ping = f"@{self.notification['account']['acct']}"
            message = ' '.join([ping, 'Here it is!!', isPublic(self.notification.status), '#autotunebot'])
            upload_video(newvid, self.video_status, self.notification, message)
        
class VideoEditRequest(BaseRequest):
    toot_video_path:tuple[str, str]
    youtube_url:str
    
    def __init__(self, toot_video:tuple[str, str], youtube_url:str, notification, video_status) -> None:
        self.toot_video = toot_video
        self.youtube_url = youtube_url
        self.notification = notification
        self.video_status = video_status
    
    def treat(self):
        ping = f"@{self.notification['account']['acct']}"
        try: newvid = vocoder.autotune_add_music(self.toot_video, self.youtube_url)
        except Exception as err: 
            print(err)
            requests_schedule.append(BadRequest(f'I couldn\'t treat your request, please report this issue on Github. ({str(err)})', self.notification))
        else:
            message = ' '.join([ping, 'Here\'s an edit with your music added!!', isPublic(self.notification.status), '#videoeditbot'])
            upload_video(newvid, self.video_status, self.notification, message)



def wait_for_ratelimit():
    'Yield until the bot can query again'
    if client.ratelimit_remaining > 0: 
        sleep(10)

    while True:
        if client.ratelimit_remaining <= 0:
            print('expired rate limit, waiting', client.ratelimit_reset - time() )
            sleep(5)
        else: break

def getYoutubeUrlInSoup(soup: BeautifulSoup):
    links = soup.find_all('a', href=True)
    youtube_links = [
        link['href'] 
        for link in links 
        if any(youtube_variant in link['href'] for youtube_variant in ['youtube.com', 'youtu.be'])
    ]
    if len(youtube_links) == 0:
        return None
    return youtube_links[0]

def check_notifications():
    'Check notifications and schedule the requests'
    notifications = client.notifications()

    for notification in notifications:
        if notification.type == 'mention':
            print(notification)
            soup = BeautifulSoup(notification.status.content, 'html.parser') # c'est un html

            try: video_status = client.status(notification.status.in_reply_to_id)
            except MastodonNotFoundError: 
                print(notification.status)
                print("Isn't replying to any status")
                requests_schedule.append(BadRequest('''It looks like you are not replying to any status. 
                It may happens because the video you want me to autotune have been posted too early, wait a bit and try again.''', notification))
                continue
                
            vid = None
            is_a_gif = False
            if 'it works' in soup.text.lower():
                requests_schedule.append(BadRequest('I\'m here to help!', notification))
                continue

            print("Trying to download the OP's video")
            for attachment in video_status['media_attachments']:
                if attachment['type'] == 'video':
                    vid = vocoder.download_url(attachment['url'])
                    break
            if not vid: # try to download the gif
                for attachment in video_status['media_attachments']:
                    if attachment['type'] == 'gifv':
                        vid = vocoder.download_url(attachment['url'])
                        is_a_gif = True
                        break
            if not vid: # try to download the yb video instead of the attachment
                try: 
                    vid = vocoder.downloadyt(BeautifulSoup(video_status.content, 'html.parser').text)
                except Exception: 
                    print(video_status['media_attachments'])
                    requests_schedule.append(BadRequest('I can\'t find any video in the status you are replying too.', notification))
                    continue

            youtube_url = getYoutubeUrlInSoup(soup)
            if not youtube_url:
                requests_schedule.append(BadRequest('I can\'t find the URL to the YouYube video in your reply, please give a valid YouTube URL', notification))
                continue
            
            print("Adding request to schedule")
            if is_a_gif or ('&add' in soup.text):
                requests_schedule.append(
                    VideoEditRequest(vid, youtube_url, notification, video_status)
                )
            else:
                requests_schedule.append(
                    AutotuneRequest(vid, youtube_url, notification, video_status)
                )

    if len(notifications) > 0:
        return True # reduce the number of requests by one

def treat_requests():
    for request in requests_schedule:
        try: 
            request.treat()
        except Exception as err: 
            print(err)
            raise err
        finally: 
            request.destroy()

        # def send_media():
        #     pass

        # def error_message():
        #     ping = f"@{request.status_to_reply['account']['acct']}"

        # ping = f"@{request.status_to_reply['account']['acct']}"

        # answer = f"{ping} THERE ARE [[pipis]] IN YOUR MAILBOX"

        # client.media_post(file_data, 'video/mp4', 'test description', in_reply_to_id=request.status_to_reply.status)

def remove_all_toots():
    'Killswitch to remove toots posted by the bot'
    for status in client.account_statuses(
        client.me()
    ):
        wait_for_ratelimit()
        client.status_delete(status)

def work():
    can_clear_notifications = check_notifications()
    treat_requests()
    if can_clear_notifications: client.notifications_clear()
    print(f'i still have {client.ratelimit_remaining} requests left')
    wait_for_ratelimit()

client.notifications_clear()
while 1:
    work()