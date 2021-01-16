#!/usr/bin/env python
# veilleesr-bots/favretweet.py

import tweepy
import logging
from config import create_api
import json
import time
from random import randrange
import threading


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class FavRetweetListener(tweepy.StreamListener):
    def __init__(self, api, tags):
        self.api = api
        self.tags = tags
        self.me = api.me()

    def on_status(self, tweet):
        logger.info(f"Processing tweet id {tweet.id}")
        if tweet.in_reply_to_status_id is not None or \
            tweet.user.id == self.me.id or \
            not any([tag in tweet.text for tag in self.tags]):
            # This tweet is a reply or I'm its author or a RT so, ignore it
            return
        #if not tweet.favorited:
        #    # Mark it as Liked, since we have not done it yet
        #    try:
        #        tweet.favorite()
        #    except Exception as e:
        #        logger.error("Error on fav", exc_info=True)
        if not tweet.retweeted:
            # Retweet, since we have not retweeted it yet
            try:
                tweet.retweet()
            except Exception as e:
                logger.error("Error on fav and retweet", exc_info=True)

        # Follow the user
        self.api.create_friendship(tweet.user.id)

    def on_error(self, status):
        logger.error(status)

class TagRetweeter(threading.Thread):
    def __init__(self, api, tags, delay=3600):
        threading.Thread.__init__(self)
        self.api = api
        self.tags = tags
        self.delay = delay

    def run(self):
        logger.info("Start tags retweeting")
        tweets_listener = FavRetweetListener(self.api, self.tags)
        stream = tweepy.Stream(self.api.auth, tweets_listener)
        stream.filter(track=self.tags, languages=["fr"], is_async = True)

        while True:
            logger.info(f"Checking thread : {stream.running}")
            if stream.running == False:
                stream.filter(track=self.tags, languages=["fr"], is_async = True)
            time.sleep(self.delay)

class AutoTweet:
    def __init__(self, api, urlfilename):
        self.api = api
        self.stream = stream
        self.tags = tags
        try :
            urlfile = open(urlfilename,"r")
            self.urls = urlfile.readlines()
        except Exception as e:
            logger.error("Error loading the url file", exc_info=True)

    def tweet(self, delay):
        i = randrange(0,len(self.urls))
        while True:
            logger.info(f"Processing url {self.urls[i]}")
            try:
                self.api.update_status(self.urls[i])
            except Exception as e:
                logger.error("Error on autotweet", exc_info=True)
            logger.info(f"Waiting to process the next url for {delay}s")
            time.sleep(delay)
            i = (i+1) % len(self.urls)

class AutoReTweet:
    def __init__(self, api, tweetidfilename, delay=72000):
        self.api = api
        self.tweetidfilename = tweetidfilename
        self.delay = delay

    def retweet(self):
        logger.info("Start auretweeting")
        while True:
            logger.info("Processing retweets")
            with open(self.tweetidfilename) as tweetidfile:
                tweetids = tweetidfile.read().splitlines()
                for tweetid in tweetids:
                    try:
                        self.api.unretweet(tweetid)
                        self.api.retweet(tweetid)
                    except Exception as e:
                        logger.error("Error on autoretweet", tweetid, exc_info=True)

            logger.info(f"Waiting to process the next tweet for {self.delay}s")
            time.sleep(self.delay)

def main():
    api = create_api()
    tags = ["#VeilleESR", "#DataESR", "#LRU", "#ESR", "#CNESER", "#MESRI", "#LPR", "#LPPR", "#LoiRecherche", "#ComESR"]

    tagRetweeter = TagRetweeter(api, tags)
    tagRetweeter.start()

    autoretweet = AutoReTweet(api, "tweet-list.txt")
    autoretweet.retweet()

if __name__ == "__main__":
    main()
