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
from random import randrange
from os import path
import argparse

import config
import mdconfig
from jorf import JORF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class AutoTweet:
    def __init__(self):
        logger.info(f"Loading config")
        self.config = config.Config.load()

        logger.info(f"Create twitter api")
        self.api = config.create_twitter_api(self.config)

        logger.info(f"Retrieving mdconfig")
        self.mdc = mdconfig.get_mdconfig(self.config.mdconfig_url)

        self.screen_name = self.api.get_settings()['screen_name']

    def tagRetweeter(self):
        c = 1 if self.config.lasttweetid == 0 else 100
        q = self.mdc['config']['tags'].strip(' ').replace(" "," OR ") + " -filter:retweets"
        logger.info("Search tweets: " + str(q), exc_info=True)
        tweets = self.api.search_tweets(q, since_id=self.config.lasttweetid, count=c, result_type='recent')
        logger.info("Found tweets: " + str(len(tweets)), exc_info=True)

        for tweet in tweets:
            if tweet.author.screen_name != self.screen_name and not tweet.retweeted:
                # Retweet, since we have not retweeted it yet
                try:
                    tweet.retweet()
                except Exception as e:
                    logger.error("Error on tagRetweet", exc_info=True)
        if len(tweets) > 0: self.config.lasttweetid = tweets[0].id

    def tweetTweeter(self):
        self.config.itweet = (self.config.itweet+1)%len(self.mdc['tweets'])
        try:
            self.api.update_status(self.mdc['tweets'][self.config.itweet])
        except Exception as e:
            logger.error("Error on tweetTweet", exc_info=True)

    def dataTweeter(self, dataTweet, in_reply_to=None):
        pm = tweepy.streaming.urllib3.PoolManager()
        img = pm.request("GET", dataTweet['imgurl'], preload_content=False)

        try:
            logger.info("Tweeting: "+str(dataTweet))
            media = self.api.simple_upload(path.basename(dataTweet['imgurl']), file = img) # filename, *, file, chunked, media_category, additional_owners
            self.api.create_media_metadata(media.media_id,dataTweet['alt'])
            if in_reply_to is None:
                tweet = self.api.update_status(
                    dataTweet['text']+"\n\n"+dataTweet['url'],
                    media_ids = [media.media_id])
            else:
                tweet = self.api.update_status(
                    dataTweet['text'],
                    in_reply_to_status_id = in_reply_to,
                    media_ids = [media.media_id])
        except Exception as e:
            logger.error("Error on dataTweet", exc_info=True)

        return tweet

    def dataRandTweeter(self):
        i = randrange(0, len(self.mdc['datatweets']))
        dt = self.mdc['datatweets'][i]
        self.dataTweeter(dt)

    def tweetmd(self,url):
        dataTweets = mdconfig.get_datamd(url)
        id = path.basename(dataTweets[0]['url'])
        for dt in dataTweets:
            tweet = self.dataTweeter(dt, in_reply_to = id)
            id = tweet.id
            logger.info("Twitté en réponse : "+str(id))
            #return


    def jorfTweeter(self, since):
        try:
            jorf = JORF(self.config)
            jorf.get_sommaire(since)

            in_reply_to = None
            for jot in jorf.get_jotweets():
                logger.info("Tweeting JORF:"+jot['id'])
                media = self.api.simple_upload(jot['id'], file = jot['img']) # filename, *, file, chunked, media_category, additional_owners
                tweet = self.api.update_status(
                    jot['text'],
                    in_reply_to_status_id = in_reply_to,
                    media_ids = [media.media_id]
                    )
                in_reply_to = tweet.id
                jot['img'].close()

        except Exception as e:
            logger.error("Error on jorfTweeter", exc_info=True)

    def lastJorfTweeter(self):
        self.jorfTweeter(self.config.last_jorf)
        self.config.reset_last_jorf()

    def recapJorfTweeter(self):
        self.jorfTweeter(self.config.last_recap)
        self.config.reset_last_recap()


    def start(self):
        while True:

            delay = int(self.mdc['config']['delay'])
            logger.info(f"Waiting for the next loop for {delay}s")
            time.sleep(delay)

def main():
    parser = argparse.ArgumentParser(description='Bot twitter pour la cpesr')
    parser.add_argument('--retweet', dest='retweet', action="store_const", const=True, default=False,
                        help="Retweete les hashtags configurés")
    parser.add_argument('--tweet', dest='tweet', action="store_const", const=True, default=False,
                        help="Tweete le message configuré suivant")
    parser.add_argument('--datarand', dest='datarand', action="store_const", const=True, default=False,
                        help="Tweete un graphique data random")
    parser.add_argument('--tweetmd', dest='tweetmd', nargs=1,
                        metavar='data_md_url',
                        help="Tweete tous les graphiques d'un md")
    parser.add_argument('--jorf', dest='jorf', action="store_const", const=True, default=False,
                        help="Tweete le dernier JO")
    parser.add_argument('--jorfrecap', dest='jorfrecap', action="store_const", const=True, default=False,
                        help="Tweete un reécapitulatif des derniers JO")
    parser.add_argument('--createconfig', dest='createconfig', action="store_const", const=True, default=False,
                        help="Crée le fichier de configuration")


    args = parser.parse_args()

    if args.createconfig:
        config.Config.load()

    autotweet = AutoTweet()

    if args.retweet:
        autotweet.tagRetweeter()
    if args.tweet:
        autotweet.tweetTweeter()
    if args.datarand:
        autotweet.dataRandTweeter()
    if args.tweetmd is not None:
        autotweet.tweetmd(args.tweetmd[0])
    if args.jorf:
        autotweet.lastJorfTweeter()
    if args.jorfrecap:
        autotweet.recapJorfTweeter()

    autotweet.config.save()

if __name__ == "__main__":
    main()
