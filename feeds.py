
# feed_urls = [
#     #"https://news.google.com/rss?hl=en-AU&gl=AU&ceid=AU:en"#,
#     # "https://www.reddit.com/r/singularity/.rss",
#     # "https://www.reddit.com/r/australian/.rss",
#     # "https://www.reddit.com/r/worldnews/.rss",
#     # "https://www.reddit.com/r/Showerthoughts/.rss",
#     "https://www.reddit.com/r/space/comments/.rss"
# ]
import pprint
from datetime import datetime, timezone, timedelta
import pytz as pytz

from reddit_rss_reader.reader import RedditRSSReader


reader = RedditRSSReader(
    url="https://www.reddit.com/r/Singularity/comments/.rss?sort=new"
    # url="http://www.reddit.com/user/LazilyAddicted/.rss"
)

# To consider comments entered in past 5 days only
# since_time = datetime.utcnow().astimezone(pytz.utc) + timedelta(days=-0.5)
since_time = datetime.now(timezone.utc).astimezone(pytz.utc) + timedelta(hours=-1)

# datetime.datetime.now(datetime.UTC)

# fetch_content will fetch all contents if no parameters are passed.
# If `after` is passed then it will fetch contents after this date
# If `since_id` is passed then it will fetch contents after this id
reviews = reader.fetch_content(
    after=since_time
)

pp = pprint.PrettyPrinter(indent=4)
for review in reviews:
    pp.pprint(review.__dict__)