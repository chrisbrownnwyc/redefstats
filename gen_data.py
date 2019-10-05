import re
import praw
import json
import sys
from config import *

reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     password=password,
                     user_agent=user_agent,
                     username=username)

def parse_added_kicked(submission):
    check_kicked = False
    check_added = False
    kicked = {}
    added = {}
    for l in submission.selftext.splitlines():
        l = l.strip()  # kill all leading and trailing whitespace
        if l in ['Kicked users:', 'Users removed']:
            check_kicked = True
            check_added = False
        elif l in ['Added users:', 'New users']:
            check_kicked = False
            check_added = True

        if '\#' in l:
            try:
                matches = re.search('^[^#]+#([0-9]+)\s\-?\s?/u/([^\s$]+)', l)
                rank = matches.group(1)
                this_user = matches.group(2).lower()

                if check_kicked:
                    kicked[this_user] = rank
                elif check_added:
                    added[this_user] = rank
            except ValueError:
                pass

    return added, kicked

def parse_rank(flair_text):
    rmatch = re.search('#(\d+)', str(flair_text))
    rank = ''
    if rmatch:
        rank = rmatch.group(1)

    return rank

def get_current_subscribers():
    subscribers = {}
    check_on = False
    break_after = False
    for post in reddit.subreddit('Redefinition').new():
        
        if post.author == 'Redefiner':
            if check_on:
                break_after = True
            else:
                # get any newly added in case they didn't comment yet
                added, kicked = parse_added_kicked(post)
                for u, r in added.items():
                    subscribers[u] = r
                check_on = True
                continue
                

        if check_on:
            if post.author and not subscribers.get(str(post.author)):
                rank = parse_rank(post.author_flair_text)
                user = str(post.author)
                subscribers[user.lower()] = rank

            post.comments.replace_more(limit=None, threshold=0)
            for c in post.comments.list():
                if c.author and not subscribers.get(str(c.author)):
                    rmatch = re.search('#(\d+)', str(c.author_flair_text))
                    rank = rmatch.group(1)
                    user = str(c.author)
                    subscribers[user.lower()] = rank

        if break_after:
            break

    return subscribers
    



def parse_all_time():
    kicked_list = []
    added_list = []
    users = {}

    def set_user_status(status, user, rank, post_date=None):
        if not users.get(user):
            users[user] = {
                'start_rank': None,
                'end_rank': None,
                'current_rank': None,
                'added_date': None,
                'kick_date': None
            }
        if status == 'kicked':
            users[user]['kick_date'] = post_date
            users[user]['end_rank'] = rank
        elif status == 'added':
            users[user]['added_date'] = post_date
            users[user]['start_rank'] = rank
        elif status == 'current':
            users[user]['current_rank'] = rank

    posts = reddit.subreddit('Redefinition').search(
        'title:Bot Recap author:Redefiner',
        sort='new',
        limit=None
    )
    for submission in posts:
        check_kicked = False
        check_added = False
        post_date = submission.title.split(' ')[0]
        
        added, kicked = parse_added_kicked(submission)

        for this_user, rank in added.items():
            set_user_status('added', this_user, rank, post_date)

        for this_user, rank in kicked.items():
            set_user_status('kicked', this_user, rank, post_date)
    
    subscribers = get_current_subscribers()
    for user, rank in subscribers.items():
        set_user_status('current', user, rank)
    
    return users

if __name__ == '__main__':
    try:
        command = sys.argv[1]
    except IndexError:
        command = 'generate'


    if command == 'subscribers':
        print(get_current_subscribers())

    elif command == 'generate':
        datafh = open('data.json', 'w')
        json.dump(parse_all_time(), datafh)
        datafh.close()

