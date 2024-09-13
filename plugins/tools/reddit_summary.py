import sys
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)
function_name = {"function":"reddit_summary"}
# Add the project root directory to the Python path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_dir))

from outsourcing import OutSource
outsource = OutSource()
def reddit_summary(date=None, **kwargs):
    outsource = OutSource()
    try:
        logger.info('Getting reddit summary')
        summary = outsource.reddit_summary()
        logger.info('Formatting Reddit summary')
        
        formatted_summary = "Reddit Summary:\n\n"
        for subreddit, posts in summary.items():
            formatted_summary += f"r/{subreddit}:\n"
            for i, post in enumerate(posts, 1):
                formatted_summary += f"{i}. {post['title']}\n"
                formatted_summary += f"   Score: {post['score']}, Comments: {post['num_comments']}\n"
                formatted_summary += f"   URL: {post['url']}\n"
                if post['selftext']:
                    formatted_summary += f"   Content: {post['selftext'][:100]}...\n"
                formatted_summary += "\n"
            formatted_summary += "\n"
        
        logger.info('Returning formatted Reddit summary')
        return formatted_summary
    except Exception as e:
        logger.error(f'Failed to get reddit summary: {str(e)}', exc_info=True)
        return f'Failed to get reddit summary: {str(e)}'
def get(name="none"):
    return "reddit_summary"

#function_name = {"function":"get_current_date"}
openai_function_schema = {
        "type": "function",
        "function": {
            "name": "reddit_summary",
            "description": "Get a summary of the hot posts from your users favorite subreddits. Call this when the user asks for reddit posts",
            "parameters": {
                "type": "object",
                "properties": {
                    "posts": {
                        "type": "string",
                        "description": "summary"
                    }
                },
                "required": ["posts"],
                "additionalProperties": False
            }
        }
    }


anthropic_tool_schema = {
    "type": "function",
    "function": {
        "name": "reddit_summary",
        "description": "Get summary of reddit posts.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


# Example usage
# if __name__ == "__main__":
#   #  print(reddit_summary())