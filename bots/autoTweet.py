# MIT License
#
# Copyright (c) 2021 Julien Gossa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

#!/usr/bin/env python

import tweepy
import logging
import time
from os import path
import argparse
import re

import vbconfig
import mdconfig
from jorf import JORF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

pm = tweepy.streaming.urllib3.PoolManager()




class AutoTweet:
    def __init__(self, config):
        self.config = config

        logger.info(f"Create twitter api")
        self.api = vbconfig.create_twitter_api(self.config)

        self.screen_name = self.api.get_settings()['screen_name']

    def tagRepost(self, tags, and_follow = True):
        c = 1 if self.config.lasttweetid == 0 else 100
        q = tags.strip(' ').replace(" "," OR ") + " -filter:retweets"
        logger.info("Search tweets: " + str(q), exc_info=True)
        tweets = self.api.search_tweets(q, since_id=self.config.lasttweetid, count=c, result_type='recent')
        logger.info("Found tweets: " + str(len(tweets)), exc_info=True)

        for tweet in tweets:
            if tweet.author.screen_name != self.screen_name and not tweet.retweeted:
                # Retweet, since we have not retweeted it yet
                try:
                    tweet.retweet()
                    if and_follow: tweet.author.follow()
                except Exception as e:
                    logger.error("Error on tagRetweet", exc_info=True)
        if len(tweets) > 0: self.config.lasttweetid = tweets[0].id

    def tweetRetweeter(self):
        for rt in self.config.retweets:
            logger.info("TweetRetweeter: " + rt +":"+str(self.config.retweets[rt]), exc_info=True)
            try:
                tweets = self.api.retweet(id = self.config.retweets[rt])
            except tweepy.errors.Forbidden:
                tweets = self.api.unretweet(id = self.config.retweets[rt])
                tweets = self.api.retweet(id = self.config.retweets[rt])
                pass
            except tweepy.errors.NotFound:
                logger.error("TweetRetweeter: Tweet non trouvé", exc_info=True)
                pass

    def post(self, text):
        try:
            self.api.update_status(text)
        except Exception as e:
            logger.warning("Error on post tweet", exc_info=True)

    def postData(self, dataTweet, in_reply_to=None):
        img = pm.request("GET", dataTweet['imgurl'], preload_content=False)
        try:
            logger.info("Tweeting: "+str(dataTweet))
            media = self.api.simple_upload(path.basename(dataTweet['imgurl']), file = img) # filename, *, file, chunked, media_category, additional_owners
            self.api.create_media_metadata(media.media_id,dataTweet['alt'])
            if in_reply_to is None:
                tweet = self.api.update_status(
                    dataTweet['text']+"\n\n"+dataTweet['twurl'],
                    media_ids = [media.media_id])
            else:
                tweet = self.api.update_status(
                    dataTweet['text'],
                    in_reply_to_status_id = in_reply_to,
                    media_ids = [media.media_id])
        except Exception as e:
            logger.error("Error on dataTweet", exc_info=True)

        img.release_conn()

        return tweet



    def postJorf(self, jotweets, img_close = False):
        try:
            in_reply_to = None
            twid = None
            for jot in jotweets:
                logger.info("Tweeting JORF:"+jot['id'])
                jot['img'].seek(0)
                media = self.api.simple_upload(jot['id'], file = jot['img']) # filename, *, file, chunked, media_category, additional_owners
                try:
                    tweet = self.api.update_status(
                        jot['text'],
                        in_reply_to_status_id = in_reply_to,
                        media_ids = [media.media_id]
                        )
                except tweepy.errors.BadRequest:
                    tweet = self.api.update_status(
                        jot['text'],
                        in_reply_to_status_id = in_reply_to
                        )
                if in_reply_to is None:
                    twid = tweet.id
                in_reply_to = tweet.id
                if img_close: jot['img'].close()
            return twid
        except Exception as e:
            logger.error("Error on jorfTweeter", exc_info=True)



    def getThread(self, root = None, tweetid = None):
        logger.info(f"Get twitter thread "+str(tweetid))

        if root is None :
            root = self.api.get_status(tweetid, tweet_mode="extended")
        if tweetid is None :
            tweetid = root.id

        tweets = self.api.user_timeline(user_id = root.author.id,
            since_id=tweetid, count=200, include_rts=False, tweet_mode="extended")
        tweets.reverse()

        res = [root]
        for t in tweets:
            #print("- "+str(t.id)+" : "+t.text)
            if t.in_reply_to_status_id == tweetid:
                #print("ok")
                res.append(t)
                tweetid = t.id

        return res

    def getTagThreads(self, tags):
        logger.info(f"Get twitter tag threads "+str(tags))

        c = 10 if self.config.lastthreadid == 0 else 100
        q = tags.strip(' ').replace(" "," OR ") + " -filter:retweets"
        logger.info("Search tweets: " + str(q), exc_info=True)
        s = self.api.search_tweets(q, since_id=self.config.lastthreadid, count=c, result_type='recent', tweet_mode = "extended")
        tweets = [ t for t in s if t.author.screen_name != self.screen_name ]
        logger.info("Found tweets: " + str(len(tweets)), exc_info=True)

        threads = []
        for t in tweets: threads.append(self.getThread(t))

        return threads


def main():
    config = vbconfig.Config.load()
    autotweet = AutoTweet(config)
    t = autotweet.api.get_status(1591179258726318080, tweet_mode="extended")
    print(t.full_text)



if __name__ == "__main__":
    main()
