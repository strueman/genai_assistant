import os
from connector import LLMConnector
import praw
from pathlib import Path
import configparser

class OutSource():
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        config = configparser.ConfigParser()
        # Get the directory of the current file (outsourcing.py)
        current_dir = Path(__file__).resolve().parent
        # Construct the path to settings.cfg
        config_path = current_dir / 'settings.cfg'
        config.read(str(config_path))
        return config

    def ask_claude_code_writer(prompt,user_id=None,session_id=None):
        system_prompt = "You are a programmer, you are tasked with writing code to complete a task. You are providing the code to an LLM based AGI to run the code and provide the output. You are also providing the context of the task and the code that is required to complete the task. You are responisble for ensuring the code is correct and effecient and that it will run without errors. "
        claude_connector = LLMConnector(provider='anthropic')
        model = 'claude-3-5-sonnet-20240620'
        response = claude_connector.chat(user_prompt=prompt, system_prompt=system_prompt, model=model, temperature=0.2)#, max_tokens=16384)
        return response['text']


    def ask_claude_problem_solver(prompt,user_id=None,session_id=None):
        system_prompt = 'You are instructing a LLM based AGI to solve a problem. You are providing the steps to solve the problem, the answer to the problem, and the context of the problem. You are responisble for ensuring the answer is correct and well thought out.'
        claude_connector = LLMConnector(provider='anthropic')
        model = 'claude-3-haiku-20240307'
        response = claude_connector.chat(user_prompt=prompt, system_prompt=system_prompt, model=model)#, temperature=0.2, max_tokens=16384)
        return response['text']
    

    def reddit_summary(self):
        try:
            # Load Reddit credentials from config
            client_id = self.config['reddit']['client_id']
            client_secret = self.config['reddit']['client_secret']
            username = self.config['reddit']['username']
            password = self.config['reddit']['password']

            # Initialize the Reddit API client
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                password=password,
                user_agent="MyRedditApp/1.0"
            )

            results = {}
            # Get the user's favorited subreddits
            for subreddit in reddit.user.subreddits(limit=10):
                if subreddit.user_has_favorited:
                    hot_posts = []
                    for post in subreddit.hot(limit=10):
                        hot_posts.append({
                            'title': post.title,
                            'url': post.url,
                            'score': post.score,
                            'num_comments': post.num_comments,
                            'selftext': post.selftext  # This is the main post content
                        })
                    results[subreddit.display_name] = hot_posts
            return results
        except Exception as e:
            print(f"Failed to get reddit summary: {e}")
            return None

    def fetch_feeds(user_id=None,session_id=None):
        pass

    def check_email(user_id=None,session_id=None):
        pass

    def check_social_media(user_id=None,session_id=None):
        pass

    def check_news(user_id=None,session_id=None):
        pass
    
    def check_calendar(user_id=None,session_id=None):
        pass

    def check_tasks(user_id=None,session_id=None):
        pass

    def check_or_create_notes(user_id=None,session_id=None):
        pass

    def research(user_id=None,session_id=None):
        pass

    def write_email(user_id=None,session_id=None):
        pass

    def write_social_media_post(user_id=None,session_id=None):
        pass
    
# print('Code Writer\n')

# print(ask_claude_code_writer('write a function that takes a list of numbers and returns the sum of the numbers'))

# print('Problem Solver\n')
# print(ask_claude_problem_solver('what is the capital of the moon?'))

# Example usage
# outsource = OutSource()
# hot_posts = outsource.reddit_summary()

# for subreddit, posts in hot_posts.items():
#     print(f"\nHot 5 posts from r/{subreddit} (Favorited):")
#     for post in posts:
#         print(f"- Title: {post['title']}")
#         print(f"  Score: {post['score']}, Comments: {post['num_comments']}")
#         print(f"  Content: {post['selftext']}")  # Print the entire post content
#         print()