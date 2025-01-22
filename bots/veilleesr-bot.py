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

import traceback


import vbconfig
import mdconfig
from jorf import JORF
from apiTwitter import APITwitter
from apiMastodon import APIMastodon
from apiBluesky import APIBluesky

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

logger.info(f"Loading config")
config = vbconfig.Config.load()

logger.info(f"Retrieving mdconfig")
mdc = mdconfig.get_mdconfig(config.get("mdconfig_url"))

apitwitter = None
apitwitter_jg = None
apimasto = None
apimasto_jg = None
apibsky = None

def veilleesr():
    logger.info("veilleesr")

    logger.info("Veille on Bluesky since "+config.get('last_veille_bsky_id'))
    bsv = apibsky.getVeille(config.get('last_veille_bsky_id'))
    for vpost in bsv:
        try:
            if vpost['author'] == 'juliengossa.cpesr.fr':
                vthread = apibsky.getVThread(vpost['raw'])
                apimasto_jg.postVThread(vthread)
                if apitwitter_jg: apitwitter_jg.postVThread(vthread)
            else:
                if "#veilleesr" not in vpost['text'].lower(): continue
                if not vpost['card']: continue
                apimasto.importVPost(vpost)
                if apitwitter: apitwitter.importVPost(vpost)
        except Exception as e:
            logger.error("Error posting vpost "+str(e))
            traceback.print_exc()

    if len(bsv) > 0: config.set('last_veille_bsky_id',bsv[-1]['id'])

    logger.info("Veille on Mastodon since "+str(config.get('last_veille_masto_id')))
    try:
        mav = apimasto.getVeille(config.get('last_veille_masto_id'))
    except Exception as e:
        logger.error("Error veille on masto "+str(e))
        mav = []
    for vpost in mav:
        try:
            apibsky.importVPost(vpost)
            if apitwitter: apitwitter.importVPost(vpost)
        except Exception as e:
            logger.error("Error posting vpost "+str(e))

    if len(mav) > 0: config.set('last_veille_masto_id', mav[0]['id'])

def postJorf(test=False):
    jorf = JORF(config.get("piste_client_id"),config.get("piste_client_secret"), config.get("wk_path"))
    jorf.get_sommaire(config.get("last_jorf"))
    joposts = jorf.get_joposts(False)
    config.reset_last_jorf()

    if test:
        print(joposts)
        return None

    try:
        apibsky.postVThread(joposts)
    except:
        logger.error("Error posting thread on BS")
    try:
        apimasto.postVThread(joposts)
    except:
        logger.error("Error posting thread on Masto")
    try:
        if apitwitter: apitwitter.postVThread(joposts)
    except:
        logger.error("Error posting thread on X")


def broadcast(vpost):
    apibsky.postVPost(vpost)
    apimasto.postVPost(vpost)
    if apitwitter: apitwitter.postVPost(vpost)

def bskyrecap():
    tops = apibsky.postRecap()

def bskydnszone():
    dnsz = apibsky.getDNSZone()
    print(dnsz)


def main():
    parser = argparse.ArgumentParser(description='Bot twitter pour la cpesr')
    parser.add_argument('--veilleesr', dest='veilleesr', action="store_const", const=True, default=False,
                        help="Effectue la veille ESR")
    parser.add_argument('--bskyrecap', dest='bskyrecap', action="store_const", const=True, default=False,
                        help="Effectue le recap bluesky")
    parser.add_argument('--post', dest='post', action="store_const", const=True, default=False,
                        help="Poste le message configuré suivant")
    parser.add_argument('--datarand', dest='datarand', action="store_const", const=True, default=False,
                        help="Poste un graphique data random")
    # parser.add_argument('--postmd', dest='postmd', nargs=1,
    #                     metavar='data_md_url',
    #                     help="Poste tous les graphiques d'un md dans un thread")

    parser.add_argument('--jorf', dest='jorf', action="store_const", const=True, default=False,
                        help="Tweete le dernier JO")
    parser.add_argument('--jorfrecap', dest='jorfrecap', action="store_const", const=True, default=False,
                        help="Tweete un reécapitulatif des derniers JO")

    parser.add_argument('--bskydnszone', dest='bskydnszone', action="store_const", const=True, default=False,
                        help="Obtient la zone DNS pour les certification bsky")

    parser.add_argument('--createconfig', dest='createconfig', action="store_const", const=True, default=False,
                        help="Crée le fichier de configuration")
    parser.add_argument('--test', dest='test', action="store_const", const=True, default=False,
                        help="Ne poste rien en ligne (en dev)")


    args = parser.parse_args()

    global apitwitter
    global apitwitter_jg
    global apimasto
    global apimasto_jg
    global apibsky
    config.test = args.test

    # try:
    #     apitwitter = APITwitter(
    #         config.get("TWITTER_CONSUMER_KEY"),
    #         config.get("TWITTER_CONSUMER_SECRET"),
    #         config.get("TWITTER_ACCESS_TOKEN"),
    #         config.get("TWITTER_ACCESS_TOKEN_SECRET"),
    #         config.get("TWITTER_BEARER_TOKEN"),
    #         args.test
    #         )

    #     apitwitter_jg = APITwitter(
    #         config.get("TWITTERJG_CONSUMER_KEY"),
    #         config.get("TWITTERJG_CONSUMER_SECRET"),
    #         config.get("TWITTERJG_ACCESS_TOKEN"),
    #         config.get("TWITTERJG_ACCESS_TOKEN_SECRET"),
    #         config.get("TWITTERJG_BEARER_TOKEN"),
    #         args.test
    #         )
    # except Exception as e: logger.error(str(e))

    apimasto = APIMastodon(
        config.get("MASTODON_ID"),
        config.get("MASTODON_SECRET"),
        config.get("MASTODON_ACCESS_TOKEN"),
        config.get("MASTODON_BASE_URL"),
        args.test
        )

    apimasto_jg = APIMastodon(
        config.get("MASTODONJG_ID"),
        config.get("MASTODONJG_SECRET"),
        config.get("MASTODONJG_ACCESS_TOKEN"),
        config.get("MASTODON_BASE_URL"),
        args.test
        )

    logger.info("Create bluesky api")
    apibsky = APIBluesky(config.get("BSKY_USERNAME"),config.get("BSKY_PASSWORD"),args.test)


    if args.veilleesr:
        veilleesr()

    if args.bskyrecap:
        bskyrecap()

    if args.post:
        ipost = config.set("ipost",(config.get("ipost")+1)%len(mdc['posts']))
        vpost = mdc['posts'][ipost]
        logger.info("Post "+vpost['text'])
        broadcast(vpost)

    if args.datarand:
        i = randrange(0, len(mdc['dataposts']))
        vpost = mdc['dataposts'][i]
        logger.info("Post data "+vpost['text'])
        broadcast(vpost)


    # if args.tweetmd is not None:
    #     dataTweets = mdconfig.get_datamd(args.tweetmd[0])
    #     twth = None
    #     sleeptime = 0
    #     for dt in dataTweets:
    #         if twth != dt['thread']:
    #             twid = dt['twurl']
    #             twth = dt['thread']
    #             time.sleep(sleeptime)
    #         tweet = autotweet.postData(dt, in_reply_to = twid)
    #         #print(str(dt) + " : " + str(twid))
    #         twid = tweet.id
    #         #twid = int(twid) + 1
    #         sleeptime = 1


        # id = None
        # for dt in dataTweets:
        #     toot = autotoot.postData(dt, in_reply_to = id)
        #     id = toot.id


    if args.jorf:
        postJorf(test=args.test)

    if args.bskydnszone:
        bskydnszone()

    # if args.jorfrecap:
        # twid = self.jorfTweeter(self.config.last_recap, recap=True)
        # if twid is not None:
        #     self.config.retweets['jorf'] = twid
        #     self.config.reset_last_recap()



    config.save()

if __name__ == "__main__":
    main()
