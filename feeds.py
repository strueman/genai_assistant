# feed_urls = [
#     #"https://news.google.com/rss?hl=en-AU&gl=AU&ceid=AU:en"#,
#     # "https://www.reddit.com/r/singularity/.rss",
#     # "https://www.reddit.com/r/australian/.rss",
#     # "https://www.reddit.com/r/worldnews/.rss",
#     # "https://www.reddit.com/r/Showerthoughts/.rss",
#     "https://www.reddit.com/r/space/comments/.rss"
# ]
from pathlib import Path
import pprint
from datetime import datetime, timezone, timedelta
import time, json
import pytz as pytz
import configparser
from reddit_rss_reader.reader import RedditRSSReader
#time_zone = pytz.timezone('Australia/Sydney')
ua_count = 0

def get_user_agent():
    global ua_count
    user_agent = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:40.0) Gecko/20100101 Firefox/40.0',
        'Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-G990B2) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.3',
        'Mozilla/5.0 (Windows NT 6.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    ]
    current_ua = user_agent[ua_count]
    ua_count = (ua_count + 1) % len(user_agent)
    return current_ua

def load_config():
    config = configparser.ConfigParser()
    # Get the directory of the current file (outsourcing.py)
    current_dir = Path(__file__).resolve().parent
    # Construct the path to settings.cfg
    config_path = current_dir / 'settings.cfg'
    config.read(str(config_path))
    return config
config = load_config()
num_posts = int(config['reddit']['num_posts'])
urls = [json.loads(config['reddit']['urls'])]
#['https://www.reddit.com/r/singularity/hot/.rss']
time_period = int(config['reddit']['time_period'])  
current_ids = []
def get_reddit_feeds(current_ids,url):
    reader = RedditRSSReader(url, user_agent=get_user_agent())
   # print(reader)
    since_time = datetime.now(timezone.utc).astimezone(pytz.utc) + timedelta(hours=-1)
    reviews = reader.fetch_content(after=since_time)


    filtered = []
    for review in reviews[:num_posts]:
        utc_time = review.__dict__['updated']
        if utc_time.tzinfo is None or utc_time.tzinfo.utcoffset(utc_time) is None:
            utc_time = utc_time.replace(tzinfo=pytz.UTC)
        aest_time = utc_time.astimezone(pytz.timezone('Australia/Sydney'))
        australian_time = aest_time.strftime("%d/%b/%Y %H:%M:%S")
        if review.__dict__['id'] not in current_ids:
            current_ids.append(review.__dict__['id'])
            filtered.append({
                'title': review.__dict__['category'] + ': ' + review.__dict__['title'],
                'link': review.__dict__['link'],
                'text': review.__dict__['extracted_text'],
                'updated': australian_time,
                'id': review.__dict__['id']
            })
    return current_ids,filtered
while True:
    for url in urls:
        current_ids, posts = get_reddit_feeds(current_ids, url)
        print(posts)
        pp = pprint.PrettyPrinter(indent=4)
        for post in posts:
            pp.pprint(post)
            print('\n')
        time.sleep(15)
    time.sleep(300)



#review.__dict__['extracted_text'],review.__dict__['extracted_text']
#dict_keys(['title', 'link', 'id', 'content', 'extracted_text', 'image_alt_text', 'updated', 'author_uri', 'author_name', 'category'])
##https://globalnews.ca/world/feed/
# http://www.npr.org/rss/rss.php?id=1004
# http://www.abc.net.au/news/feed/51120/rss.xml News Just In
