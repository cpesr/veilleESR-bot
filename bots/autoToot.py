# MIT License
#
# Copyright (c) 2022 Julien Gossa
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
from mastodon import Mastodon
import logging
import os
import json
from datetime import datetime

from os import path
import argparse
import datetime
import re
import urllib3

import vbconfig
import mdconfig
from jorf import JORF


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()



class AutoToot:
    def __init__(self, config):
        logger.info(f"Loading config")
        self.config = config

        # logger.info(f"Create twitter api")
        # self.twitter = config.create_twitter_api(self.config) if twitter is None else twitter

        logger.info(f"Create mastodon api")
        self.api = vbconfig.create_mastodon_api(self.config)

        self.user_id = self.api.me().id

    def tagRepost(self, tags, and_follow = True):
        toots = []
        for tag in tags.split(' '):
            logger.info("Search toots: " + tag)
            toots += self.api.timeline_hashtag(tag.strip(" #"), since_id = self.config.lasttootid)

        logger.info("Found toots: " + str(len(toots)), exc_info=True)

        for toot in toots:
            if toot.account.id != self.user_id:
                try:
                    self.api.status_reblog(toot.id)
                    if and_follow: self.api.account_follow(toot.account.id)
                except Exception as e:
                    logger.error("Error on tagRetoot", exc_info=True)
        if len(toots) > 0: self.config.lasttootid = toots[0].id

    def post(self, text):
        try:
            self.api.status_post(text)
        except Exception as e:
            logger.error("Error on post toot", exc_info=True)


    def postData(self, dataTweet, in_reply_to=None):
        pm = tweepy.streaming.urllib3.PoolManager()
        img = pm.request("GET", dataTweet['imgurl'], preload_content=False)
        toot = None
        try:
            logger.info("Tooting: "+str(dataTweet))
            media = self.api.media_post(img, mime_type = img.headers['Content-Type'])
            #self.api.create_media_metadata(media.media_id,dataTweet['alt'])
            if in_reply_to is None:
                toot = self.api.status_post(dataTweet['text']+"\n\n"+dataTweet['url'], media_ids = [media.id])
            else:
                toot = self.api.status_post(dataTweet['text'], in_reply_to_id = in_reply_to, media_ids = [media.id])
        except Exception as e:
            logger.error("Error on postData toot", exc_info=True)

        return toot

    def postJorf(self, jotoots, img_close = False):
        try:
            in_reply_to = None
            tid = None
            for jot in jotoots:
                logger.info("Tooting JORF:"+jot['id'])
                jot['img'].seek(0)
                media = self.api.media_post(jot['img'], mime_type='image/png')
                try:
                    toot = self.api.status_post(
                        jot['text'],
                        in_reply_to_id = in_reply_to,
                        media_ids = [media.id] )
                except Exception as e:
                    logger.error("Error on jorfTooter", exc_info=True)
                    toot = self.api.status_post(
                        jot['text'],
                        in_reply_to_id = in_reply_to)
                if in_reply_to is None:
                    tid = toot.id
                in_reply_to = toot.id
                if img_close: jot['img'].close()
            return tid
        except Exception as e:
            logger.error("Error on jorfTooter", exc_info=True)


    def postTwitterThreadOnMastodon(self, tt):
        logger.info(f"Post Twitter thread "+str(tt[0].id)+" on Mastodon")
        pm = urllib3.PoolManager()
        mid = None
        tt[0].full_text = re.sub("https://t.co/.*", "", tt[0].full_text)+"\n\nPar "+tt[0].author.name+" @"+tt[0].author.screen_name+"@twitter.com"
        for t in tt:
            text = re.sub("https://t.co/.*", "", t.full_text)
            media_ids = []
            try:
                for media in t.entities['media']:
                    #urllib.request.urlretrieve(media['media_url'], "/tmp/t2m_media")
                    #mm = self.mastodon.media_post("/tmp/t2m_media")
                    img = pm.request("GET", media['media_url'], preload_content=False)
                    mm = self.api.media_post(img, mime_type = img.headers['Content-Type'])
                    media_ids.append(mm.id)
            except Exception:
                pass

            m = self.api.status_post(text, in_reply_to_id = mid, media_ids = media_ids)
            mid = m.id

        self.api.status_post("Post original :\nhttps://twitter.com/"+tt[0].author.screen_name+"/status/"+str(tt[0].id), in_reply_to_id = mid)

    def postTagThreads(self, threads):
        for tt in threads:
            self.postTwitterThreadOnMastodon(tt)

    def deleteAllToots(self):
        for m in self.api.timeline():
            print(m.get("id"))
            self.api.status_delete(m.get("id"))

def main():
    autotoot = AutoToot()
    #autotoot.tagRetweeter()

    jorf = JORF(autotoot.config)
    jorf.get_sommaire(autotoot.config.last_jorf)
    jots = jorf.get_jotweets(False)

    tid = autotoot.postJorf(jots)


if __name__ == "__main__":
    main()
