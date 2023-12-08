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
from io import BytesIO


import vbconfig
import mdconfig
from jorf import JORF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

pm = tweepy.streaming.urllib3.PoolManager()



class APITwitter:
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret, bearer_token):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token

        logger.info(f"Create twitter api")
        # v1.1
        self.api = self.create_twitter_api_v1()
        # self.screen_name = self.api.get_settings()['screen_name']
        time.sleep(1)
        # v2
        self.client = self.create_twitter_api_v2()
        #self.screen_name = self.client.get_me().data['username']


    def create_twitter_api_v1(self):

        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_token_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True)
        try:
            api.verify_credentials()
        except Exception as e:
            logger.error("Error creating APIv1.1", exc_info=True)
            raise e
        logger.info("Twitter API v1.1 created")
        return api


    def create_twitter_api_v2(self):

        client = tweepy.Client(
                            consumer_key=self.consumer_key,
                            consumer_secret=self.consumer_secret,
                            access_token=self.access_token,
                            access_token_secret=self.access_token_secret,
                            bearer_token=self.bearer_token)
        try:
            client.get_me()
        except Exception as e:
            logger.error("Error creating APIv2", exc_info=True)
            raise e
        logger.info("Twitter API v2 created")

        return client

    def uploadImage(self, image):
        if 'url' in image:
            img = pm.request("GET", image['url'], preload_content=False)
            media = self.api.simple_upload(path.basename(image['url']), file = img)
            img.release_conn()
        elif 'data' in image:
            media = self.api.simple_upload(image['filename'], file = BytesIO(image['data']))
        else:
            media = self.api.simple_upload(image['path'])

        self.api.create_media_metadata(media.media_id, image['alt'])

        return media

    def getVPost(self, tweet):
        vpost = {
            'text': tweet.text,
            'author': tweet.author.screen_name,
            'id': tweet.id,
            'url': None,
            'images': [],
            'platform': "twitter",
            'raw': tweet }

        return vpost

    def postVPost(self, vpost, in_reply_to=None):
        cardurl = ("\n\n" + vpost['cardurl']) if 'cardurl' in vpost else ""
        maxtxtlen = 279 - len(cardurl)
        text = vpost['text'][0:maxtxtlen] + cardurl

        media_ids = []
        if 'images' in vpost:
            for image in vpost['images']:
                media = self.uploadImage(image)
                media_ids.append(media.media_id)

        tweet = self.client.create_tweet(
            text = text,
            in_reply_to_tweet_id = in_reply_to,
            media_ids = media_ids if len(media_ids)>0 else None)

        return tweet

    def postVThread(self, vthread):
        irp = None
        for vpost in vthread:
            tweet = self.postVPost(vpost, in_reply_to = irp)
            irp = tweet.data['id']

    def importVPost(self, vpost):
        tweet = self.client.create_tweet(
            text="[#VeilleESR] "+vpost['card']['title']+"\n\n"+vpost['card']['url']+"\n\nVia "+vpost['url']
        )

    def postJorf(self, jotweets, img_close = False):
        try:
            in_reply_to = None
            twid = None
            for jot in jotweets:
                logger.info("Tweeting JORF:"+jot['id'])
                jot['img'].seek(0)
                media = self.api.simple_upload(jot['id'], file = jot['img']) # filename, *, file, chunked, media_category, additional_owners
                try:
                    tweet = self.client.create_tweet(
                        text = jot['text'],
                        in_reply_to_tweet_id = in_reply_to,
                        media_ids = [media.media_id]
                        )
                except tweepy.errors.BadRequest:
                    tweet = self.client.create_tweet(
                        text = jot['text'],
                        in_reply_to_tweet_id = in_reply_to
                        )
                if in_reply_to is None:
                    twid = tweet.data['id']
                in_reply_to = tweet.data['id']
                if img_close: jot['img'].close()
            return twid
        except Exception as e:
            logger.error("Error on jorfTweeter", exc_info=True)


    # def tagRepost(self, tags, and_follow = True):
    #     c = 1 if self.config.lasttweetid == 0 else 100
    #     q = tags.strip(' ').replace(" "," OR ") + " -filter:retweets"
    #     logger.info("Search tweets: " + str(q), exc_info=True)
    #     tweets = self.api.search_tweets(q, since_id=self.config.lasttweetid, count=c, result_type='recent')
    #     logger.info("Found tweets: " + str(len(tweets)), exc_info=True)
    #
    #     for tweet in tweets:
    #         if tweet.author.screen_name != self.screen_name and not tweet.retweeted:
    #             # Retweet, since we have not retweeted it yet
    #             try:
    #                 tweet.retweet()
    #                 if and_follow: tweet.author.follow()
    #             except Exception as e:
    #                 logger.error("Error on tagRetweet", exc_info=True)
    #     if len(tweets) > 0: self.config.lasttweetid = tweets[0].id
    #
    # def tweetRetweeter(self):
    #     for rt in self.config.retweets:
    #         logger.info("TweetRetweeter: " + rt +":"+str(self.config.retweets[rt]), exc_info=True)
    #         try:
    #             tweets = self.api.retweet(id = self.config.retweets[rt])
    #         except tweepy.errors.Forbidden:
    #             tweets = self.api.unretweet(id = self.config.retweets[rt])
    #             tweets = self.api.retweet(id = self.config.retweets[rt])
    #             pass
    #         except tweepy.errors.NotFound:
    #             logger.error("TweetRetweeter: Tweet non trouvé", exc_info=True)
    #             pass



    # def getThread(self, root = None, tweetid = None):
    #     logger.info(f"Get twitter thread "+str(tweetid))
    #
    #     if root is None :
    #         root = self.api.get_status(tweetid, tweet_mode="extended")
    #     if tweetid is None :
    #         tweetid = root.id
    #
    #     tweets = self.api.user_timeline(user_id = root.author.id,
    #         since_id=tweetid, count=200, include_rts=False, tweet_mode="extended")
    #     tweets.reverse()
    #
    #     res = [root]
    #     for t in tweets:
    #         #print("- "+str(t.id)+" : "+t.text)
    #         if t.in_reply_to_status_id == tweetid:
    #             #print("ok")
    #             res.append(t)
    #             tweetid = t.id
    #
    #     return res
    #
    # def getTagThreads(self, tags):
    #     logger.info(f"Get twitter tag threads "+str(tags))
    #
    #     c = 10 if self.config.lastthreadid == 0 else 100
    #     q = tags.strip(' ').replace(" "," OR ") + " -filter:retweets"
    #     logger.info("Search tweets: " + str(q), exc_info=True)
    #     s = self.api.search_tweets(q, since_id=self.config.lastthreadid, count=c, result_type='recent', tweet_mode = "extended")
    #     tweets = [ t for t in s if t.author.screen_name != self.screen_name ]
    #     logger.info("Found tweets: " + str(len(tweets)), exc_info=True)
    #
    #     threads = []
    #     for t in tweets: threads.append(self.getThread(t))
    #
    #     return threads


if __name__ == "__main__":
    config = vbconfig.Config.load()
    autotweet = AutoTweet(config)
    t = autotweet.api.get_status(1591179258726318080, tweet_mode="extended")
    print(t.full_text)
