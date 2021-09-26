#!/usr/bin/env python
# veilleesr-bots/favretweet.py

import tweepy
import logging
import time
from random import randrange
from os import path
from config import create_api
from mdconfig import get_mdconfig


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class AutoTweet:
    def __init__(self, api, mdconfig_url):
        self.api = api
        self.mdconfig_url = mdconfig_url
        self.screen_name = api.get_settings()['screen_name']

        self.itweet = -1
        self.lasttweetid = 0

    def tagRetweeter(self):
        c = 1 if self.lasttweetid == 0 else 100
        q = self.mdc['config']['tags'].strip(' ').replace(" "," OR ") + " -filter:retweets"
        logger.info("Search tweets: " + str(q), exc_info=True)
        tweets = self.api.search_tweets(q, since_id=self.lasttweetid, count=c, result_type='recent')
        logger.info("Found tweets: " + str(len(tweets)), exc_info=True)

        for tweet in tweets:
            if tweet.author.screen_name != self.screen_name and not tweet.retweeted:
                # Retweet, since we have not retweeted it yet
                try:
                    tweet.retweet()
                except Exception as e:
                    logger.error("Error on tagRetweet", exc_info=True)
        if len(tweets) > 0: self.lasttweetid = tweets[0].id

    def tweetTweeter(self):
        self.itweet = (self.itweet+1)%len(self.mdc['tweets'])
        try:
            self.api.update_status(self.mdc['tweets'][self.itweet])
        except Exception as e:
            logger.error("Error on tweetTweet", exc_info=True)

    def dataTweeter(self):
        i = randrange(0, len(self.mdc['datatweets']))
        dt = self.mdc['datatweets'][i]

        pm = tweepy.streaming.urllib3.PoolManager()
        img = pm.request("GET", dt['imgurl'], preload_content=False)

        try:
            logger.info("Tweeting: "+str(dt))
            media = self.api.simple_upload(path.basename(dt['imgurl']), file = img) # filename, *, file, chunked, media_category, additional_owners
            self.api.create_media_metadata(media.media_id,dt['alt'])
            self.api.update_status(dt['text']+"\n"+dt['url'], media_ids = [media.media_id])
        except Exception as e:
            logger.error("Error on dataTweet", exc_info=True)

    def start(self):

        while True:
            logger.info(f"Retrieving mdconfig")
            self.mdc = get_mdconfig(self.mdconfig_url)

            # Retweets
            self.tagRetweeter()

            # Tweets
            self.tweetTweeter()

            # Data
            self.dataTweeter()

            delay = int(self.mdc['config']['delay'])
            logger.info(f"Waiting for the next loop for {delay}s")
            time.sleep(delay)

def main():
    api = create_api()

    #tagRetweeter = TagRetweeter(api, tags)
    #tagRetweeter.start()

    autotweet = AutoTweet(api, "https://github.com/juliengossa/veilleesr-bot/raw/master/botconfig.md")
    autotweet.start()

if __name__ == "__main__":
    main()
