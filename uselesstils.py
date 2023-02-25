import webbrowser
from tempfile import NamedTemporaryFile
from json import dumps

# useless utils lol
def firefoxjson(text):
    with NamedTemporaryFile('w', delete=False, suffix='.json') as f:
        url = 'file://' + f.name
        f.write(dumps(text, default=str))
    webbrowser.open(url)

def remove_all_toots():
    'Killswitch to remove toots posted by the bot'
    # ok actually i don't know how to do it lol