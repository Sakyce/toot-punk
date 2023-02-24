from mastodon import Mastodon
from bs4 import BeautifulSoup

class AutotuneRequest:
    def __init__(self, video_url, youtube_query, status_to_reply) -> None:
        self.video_url = video_url
        self.youtube_query = youtube_query
        self.status_to_reply = status_to_reply

requests_schedule:list[AutotuneRequest] = []

with open('credential.secret', 'r') as file:
    creds = file.readlines()

client = Mastodon(
    api_base_url='https://botsin.space',
    client_id=creds[0],
    client_secret=creds[1],
    access_token=creds[2],
    )

def wait_for_ratelimit():
    'Yield until the bot can query again'
    while client.ratelimit_remaining <= 0: pass

def check_notifications():
    'Check notifications and schedule the requests'
    notifications = client.push_subscription()

    for notification in notifications:
        if notification.type == 'mention':
            soup = BeautifulSoup(notification.status.content) # c'est un html
            in_reply_to = client.status(notification.status.in_reply_to_id)

            video_url = None
            for attachment in in_reply_to['media_attachments']:
                if attachment['type'] == 'video':
                    video_url = attachment['url']
                    break

            requests_schedule.append(
                AutotuneRequest(video_url, soup.text, notification)
            )

def treat_requests():
    for request in requests_schedule:
        client.status_post(f"{request.status_to_reply['account']['acct']} pong maybe ?", in_reply_to_id=request.status_to_reply)

pass

while 1:
    wait_for_ratelimit()
    client.notifications_clear()