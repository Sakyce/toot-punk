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

class BaseRequest(ABC):
    def treat(self):
        pass

    def destroy(self):
        requests_schedule.remove(self)

class AutotuneRequest(BaseRequest):
    toot_video_path:tuple[str, str]
    youtube_url:str
    
    def __init__(self, toot_video:tuple[str, str], youtube_url:str, status_to_reply, video_status) -> None:
        self.toot_video = toot_video
        self.youtube_url = youtube_url
        self.status_to_reply = status_to_reply
        self.video_status = video_status
    
    def treat(self):
        newvid = vocoder.autotuneyt(self.toot_video, self.youtube_url)
        media_post = client.media_post(getfiledata(newvid), 'video/mp4')
        print('uploading to mastodon')
        sleep(10)
        ping = f"@{self.status_to_reply['account']['acct']}"
        public_reaction = 'Also, *please set your autotune request in UNLISTED*!' if self.status_to_reply.status['visibility'] == 'public' else ''
        status = client.status_post(
            ' '.join([ping, 'Here it is!!', public_reaction, '#autotune']) , 
            media_ids=media_post['id'], 
            sensitive=self.video_status['sensitive'],
            in_reply_to_id=self.status_to_reply.status,
            spoiler_text=self.video_status['spoiler_text'],
            visibility='unlisted' if self.video_status['sensitive'] else 'public'
                )
        sleep(2)
        if not self.video_status['sensitive']:
            client.status_reblog(status['id'])


class BadRequest(BaseRequest):
    def __init__(self, text, status_to_reply) -> None:
        self.text = text
        self.status_to_reply = status_to_reply
    
    def treat(self):
        ping = f"@{self.status_to_reply['account']['acct']}"
        public_reaction = 'Also, *please set your autotune request in UNLISTED*!' if self.status_to_reply.status['visibility'] == 'public' else ''
        client.status_post(' '.join([ping,  self.text, public_reaction]), visibility='unlisted', in_reply_to_id=self.status_to_reply.status)

requests_schedule:list[BaseRequest] = []

def wait_for_ratelimit():
    'Yield until the bot can query again'
    if client.ratelimit_remaining > 0: 
        sleep(10)

    while True:
        if client.ratelimit_remaining <= 0:
            print('expired rate limit, waiting', client.ratelimit_reset - time() )
            sleep(5)
        else: break

def check_notifications():
    'Check notifications and schedule the requests'
    notifications = client.notifications()

    for notification in notifications:
        if notification.type == 'mention':
            soup = BeautifulSoup(notification.status.content, 'html.parser') # c'est un html

            try: video_status = client.status(notification.status.in_reply_to_id)
            except MastodonNotFoundError: 
                print(notification.status)
                requests_schedule.append(BadRequest('''It looks like you are not replying to any status. 
                It may happens because the video you want me to autotune have been posted too early, wait a bit and try again.''', notification))
                continue
                
            vid = None
            
            for attachment in video_status['media_attachments']:
                if attachment['type'] == 'video':
                    vid = vocoder.download_url(attachment['url'])
                    break
            if not vid: # try to download the yb video instead of the attachment
                try: 
                    vid = vocoder.downloadyt(BeautifulSoup(video_status.content, 'html.parser').text)
                except Exception: 
                    requests_schedule.append(BadRequest('I can\'t find any video in the status you are replying too.', notification))
                    continue

            if not vocoder.exists(soup.text):
                print(soup.text)
                requests_schedule.append(BadRequest('I can\'t find the URL to the YouYube video in your reply, please give a valid YouTube URL', notification))
                continue

            requests_schedule.append(
                AutotuneRequest(vid, soup.text, notification, video_status)
            )

    if len(notifications) > 0:
        return True # reduce the number of requests by one

def getfiledata(filename): # 109921593256401643
    file_data = None
    with open(filename, 'rb') as file:
        file_data = file.read()
    return file_data

def treat_requests():
    for request in requests_schedule:
        try: 
            request.treat()
        except Exception as err: 
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