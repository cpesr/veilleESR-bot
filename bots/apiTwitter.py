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

logger = logging.getLogger()

pm = tweepy.streaming.urllib3.PoolManager()



class APITwitter:
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret, bearer_token, test=True):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token

        self.test = test

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
        if self.test:
            logger.info("X fake post \""+vpost['text'][0:50]+"...\"")
            return {'id':'fakeid'}

        try:
            cardurl = "\n\n" + vpost['card']['url']
            maxtxtlen = 255
        except:
            cardurl = ""
            maxtxtlen = 279
        text = re.sub(r'\s*http\S+', '', vpost['text'])
        text = text[0:maxtxtlen] + cardurl

        media_ids = []
        if 'images' in vpost:
            for image in vpost['images']:
                media = self.uploadImage(image)
                media_ids.append(media.media_id)

        tweet = self.client.create_tweet(
            text = text,
            in_reply_to_tweet_id = in_reply_to,
            media_ids = media_ids if len(media_ids)>0 else None)

        return tweet.data

    def postVThread(self, vthread):
        irp = None
        for vpost in vthread:
            tweet = self.postVPost(vpost, in_reply_to = irp)
            irp = tweet['id']

    def importVPost(self, vpost):
        if self.test:
            logger.info("X fake import \""+vpost['text'][0:50]+"...\"")
            return {}

        tweet = self.client.create_tweet(
            text="[#VeilleESR] "+vpost['card']['title']+"\n\n"+vpost['card']['url']+"\n\nVia "+vpost['url']
        )

if __name__ == "__main__":
    config = vbconfig.Config.load()
    autotweet = AutoTweet(config)
    t = autotweet.api.get_status(1591179258726318080, tweet_mode="extended")
    print(t.full_text)
