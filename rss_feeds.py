import feedparser
import configparser
import time
from connector import LLMConnector
from datetime import datetime, timedelta
from plugins.cache_api import APICache
import logging
import html
from typing import Dict, Any
import requests
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SummarizeFeeds:
    def __init__(self):
        self.cache = APICache(process_name='rss_feeds')

    def summarize(self, payload=None, links=True):
        try:
            llm = LLMConnector(provider='openai').chat
            system_prompt = "Create concise summaries from the following feeds. Do one for world news, one for Australian news, one for AI news and one for topics and newsworthy posts on r/singularity this one can be longer, also include a summary of any weather information."
            brief = llm(user_prompt=payload, system_prompt=system_prompt, model='gpt-4o-mini', temperature=0.5, max_tokens=2048)
            return brief
        except Exception as e:
            logger.error(f'Error in summarize: {e}')
            return None

class RSSFeeds:
    def __init__(self, limit=10, no_summary_urls=None, urls=None, cache_duration=900):
        config = configparser.ConfigParser()
        config.read('settings.cfg')
        if urls is None:
            urls = []
            for i in config['feeds']._options():
                urls.append(config['feeds'][i])
            self.urls = urls
        url_string = '\nFeed URLs:\n'
        for i in urls:
            url_string += f'  - {i}\n'
        logger.info(url_string)

        self.limit = limit
        self.no_summary_urls = no_summary_urls or []
        self.cache_duration = cache_duration
        self.cache = APICache(process_name='rss_feeds')

    def parse_rss_feeds(self, links=True):
        if self.cache.list_cache() is not None and 'feeds' in self.cache.list_cache():
            data = self.cache.get_cache('feeds')
            if datetime.now().timestamp() - data['timestamp'] < self.cache_duration:
                return self._format_output(data['feeds'], links=links)

        feeds = {}
        for url in self.urls:
            logger.info(f"Parsing feed {url}")
            try:
                # Fetch the content of the URL
                response = requests.get(url, timeout=10)
                response.raise_for_status()  # Raise an exception for bad status codes
                
                # Parse the content using feedparser
                feed = feedparser.parse(BytesIO(response.content))
                
                feeds[url] = {
                    'title': feed.feed.get('title', 'Untitled Feed'),
                    'entries': [{
                        'title': entry.get('title', 'Untitled Entry'),
                        'link': entry.get('link', ''),
                        'summary': '' if url in self.no_summary_urls else entry.get('summary', ''),
                        'published': entry.get('published', '')
                    } for entry in feed.entries[:self.limit]]
                }
            except requests.RequestException as e:
                logger.error(f"Error fetching feed from {url}: {str(e)}")
            except Exception as e:
                logger.error(f"Error parsing feed from {url}: {str(e)}")

        data = {
            'timestamp': datetime.now().timestamp(),
            'feeds': feeds
        }
        logger.info("Updating feeds in the cache")
        self.cache.set_cache('feeds', data)
        return self._format_output(data['feeds'], links=links)

    def _format_output(self, feeds: Dict[str, Any], links: bool = True) -> str:
        output = []
        logger.info("Starting to format output")
        for url, feed in feeds.items():
            try:
                logger.debug(f"Formatting feed: {url}")
                feed_title = html.escape(feed.get('title', 'Untitled Feed'))
                output.append(f"Feed: {feed_title}")
                
                entries = feed.get('entries', [])
                logger.debug(f"Number of entries in feed: {len(entries)}")
                
                for entry in entries:
                    try:
                        title = html.escape(entry.get('title', 'Untitled Entry'))
                        output.append(f"  - {title[:500]}")  # Limit title length
                        
                        if links:
                            link = html.escape(entry.get('link', ''))
                            output.append(f"    Link: {link[:200]}")  # Limit link length
                        
                        summary = html.escape(entry.get('summary', ''))
                        if summary:
                            output.append(f"    Summary: {summary[:2000]}...")  # Limit summary length
                        
                        published = html.escape(entry.get('published', 'No date'))
                        output.append(f"    Published: {published[:50]}")  # Limit date length
                    
                    except Exception as e:
                        logger.error(f"Error formatting entry in feed {url}: {str(e)}")
                        continue
                
                output.append("")  # Empty line between feeds
            
            except Exception as e:
                logger.error(f"Error formatting feed {url}: {str(e)}")
                continue
        
        logger.info("Finished formatting output")
        return "\n".join(output)

if __name__ == "__main__":
    logger.info("Main execution started")
    rss_feeds = RSSFeeds(limit=10)
    summarizer = SummarizeFeeds()
    cache = APICache(process_name='rss_feeds')
    while True:
        log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            feed_content = rss_feeds.parse_rss_feeds(links=False)
            summary = summarizer.summarize(payload=feed_content, links=False)
            cache.set_cache('news_brief', summary)
            logger.info(f'Updated feeds in the cache @ {log_time}')
        except Exception as e:
            logger.error(f"Error occurred at {log_time}: {str(e)}")
        time.sleep(rss_feeds.cache_duration)