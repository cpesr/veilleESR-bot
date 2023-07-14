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

import argparse
import logging
from random import randrange
import time
from os import path


import vbconfig
import mdconfig
from jorf import JORF
from autoTweet import AutoTweet
from autoToot import AutoToot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def main():
    parser = argparse.ArgumentParser(description='Bot twitter pour la cpesr')
    parser.add_argument('--tag-retweet', dest='tagRetweet', action="store_const", const=True, default=False,
                        help="Retweete les hashtags configurés")
    parser.add_argument('--tag-t2m', dest='tagt2m', action="store_const", const=True, default=False,
                        help="Transfère les threads twitter #VeilleESR vers mastodon")
    parser.add_argument('--tweet-retweet', dest='tweetRetweet', action="store_const", const=True, default=False,
                        help="Retweete les tweets configurés")
    parser.add_argument('--tweet', dest='tweet', action="store_const", const=True, default=False,
                        help="Tweete le message configuré suivant")
    parser.add_argument('--datarand', dest='datarand', action="store_const", const=True, default=False,
                        help="Tweete un graphique data random")
    parser.add_argument('--tweetmd', dest='tweetmd', nargs=1,
                        metavar='data_md_url',
                        help="Tweete tous les graphiques d'un md dans un thread")
    parser.add_argument('--jorf', dest='jorf', action="store_const", const=True, default=False,
                        help="Tweete le dernier JO")
    parser.add_argument('--jorfrecap', dest='jorfrecap', action="store_const", const=True, default=False,
                        help="Tweete un reécapitulatif des derniers JO")
    parser.add_argument('--createconfig', dest='createconfig', action="store_const", const=True, default=False,
                        help="Crée le fichier de configuration")
    parser.add_argument('--test', dest='test', action="store_const", const=True, default=False,
                        help="Ne poste rien en ligne (en dev)")


    args = parser.parse_args()

    logger.info(f"Loading config")
    config = vbconfig.Config.load()

    logger.info(f"Retrieving mdconfig")
    mdc = mdconfig.get_mdconfig(config.mdconfig_url)


    autotweet = AutoTweet(config)
    autotoot = AutoToot(config)

    if args.tagt2m:
        logger.info("tag transfer to mastodon")
        threads = autotweet.getTagThreads("#VeilleESR")
        autotoot.postTagThreads(threads)
        if len(threads) > 0: config.lastthreadid = threads[0][0].id

    if args.tagRetweet:
        logger.info("tag repost")
        #autotweet.tagRepost(mdc['config']['tags'])
        autotoot.tagRepost(mdc['config']['tags'])

    if args.tweetRetweet:
        pass
        #autotweet.tweetRetweeter()

    if args.tweet:
        config.itweet = (config.itweet+1)%len(mdc['tweets'])
        logger.info("post "+mdc['tweets'][config.itweet])
        autotweet.post(mdc['tweets'][config.itweet])
        autotoot.post(mdc['tweets'][config.itweet])

    if args.datarand:
        i = randrange(0, len(mdc['datatweets']))
        dt = mdc['datatweets'][i]
        print(dt)
        autotweet.postData(dt)
        autotoot.postData(dt)

    if args.tweetmd is not None:
        dataTweets = mdconfig.get_datamd(args.tweetmd[0])
        twth = None
        sleeptime = 0
        for dt in dataTweets:
            if twth != dt['thread']:
                twid = dt['twurl']
                twth = dt['thread']
                time.sleep(sleeptime)
            tweet = autotweet.postData(dt, in_reply_to = twid)
            #print(str(dt) + " : " + str(twid))
            twid = tweet.id
            #twid = int(twid) + 1
            sleeptime = 1


        # id = None
        # for dt in dataTweets:
        #     toot = autotoot.postData(dt, in_reply_to = id)
        #     id = toot.id


    if args.jorf:
        jorf = JORF(autotoot.config)
        jorf.get_sommaire(autotoot.config.last_jorf)
        jots = jorf.get_jotweets(False)

        if args.test:
            print(jots)
        else:
            twid = autotweet.postJorf(jots)
            toid = autotoot.postJorf(jots, img_close = True)

            if twid is not None:
                config.retweets['jorf'] = twid
                config.reset_last_jorf()

    # if args.jorfrecap:
        # twid = self.jorfTweeter(self.config.last_recap, recap=True)
        # if twid is not None:
        #     self.config.retweets['jorf'] = twid
        #     self.config.reset_last_recap()

    

    autotweet.config.save()

if __name__ == "__main__":
    main()
