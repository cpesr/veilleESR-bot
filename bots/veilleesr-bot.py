#!/usr/bin/env python
# veilleesr-bots/favretweet.py

import tweepy
import logging
from config import create_api
import json
import time
from random import randrange

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class FavRetweetListener(tweepy.StreamListener):
    def __init__(self, api):
        self.api = api
        self.me = api.me()

    def on_status(self, tweet):
        logger.info(f"Processing tweet id {tweet.id}")
        if tweet.in_reply_to_status_id is not None or \
            tweet.user.id == self.me.id:
            # This tweet is a reply or I'm its author so, ignore it
            return
        if not tweet.favorited:
            # Mark it as Liked, since we have not done it yet
            try:
                tweet.favorite()
            except Exception as e:
                logger.error("Error on fav", exc_info=True)
        if not tweet.retweeted:
            # Retweet, since we have not retweeted it yet
            try:
                tweet.retweet()
            except Exception as e:
                logger.error("Error on fav and retweet", exc_info=True)

    def on_error(self, status):
        logger.error(status)
        
class AutoTweet:
    def __init__(self, api, stream, urlfilename):
        self.api = api
        self.stream = stream
        try :
            urlfile = open(urlfilename,"r")
            self.urls = urlfile.readlines()
        except Exception as e:
            logger.error("Error loading the url file", exc_info=True)
        
    def tweet(self, delay):
    
        self.stream.filter(track=["#VeilleESR", "#DataESR", "#LRU"], languages=["fr"], is_async = True)
    
        i = randrange(0,len(self.urls))
        while True:
            logger.info(f"Checking thread : {self.stream.running}")
            if self.stream.running == False:
                self.stream.filter(track=["#VeilleESR", "#DataESR", "#LRU"], languages=["fr"], is_async = True)
        
            logger.info(f"Processing url {self.urls[i]}")
            try:
                self.api.update_status(self.urls[i])
            except Exception as e:
                logger.error("Error on autotweet", exc_info=True)
            logger.info(f"Waiting to process the next url for {delay}s")            
            time.sleep(delay)
            i = (i+1) % len(self.urls)

def main():
    api = create_api()
    tweets_listener = FavRetweetListener(api)
    stream = tweepy.Stream(api.auth, tweets_listener)
    #stream.filter(track=["#VeilleESR", "#DataESR", "#LRU", "#ESR"], languages=["fr"], is_async = True)
    
    autotweet = AutoTweet(api, stream, "url-list.txt")
    autotweet.tweet(57600)
    
    

if __name__ == "__main__":
    main()