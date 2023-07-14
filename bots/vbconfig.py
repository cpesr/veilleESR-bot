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

import tweepy
from mastodon import Mastodon
import logging
import os
import json
from datetime import datetime

logger = logging.getLogger()


def create_twitter_api_v1(config):

    if (config.twitter_consumer_key is None or
        config.twitter_consumer_secret is None or
        config.twitter_access_token is None or
        config.twitter_access_token_secret is None):
        raise Exception("CONSUMER_KEY and CONSUMER_SECRET and ACCESS_TOKEN and ACCESS_TOKEN_SECRET env var must be configured.")

    auth = tweepy.OAuthHandler(config.twitter_consumer_key, config.twitter_consumer_secret)
    auth.set_access_token(config.twitter_access_token, config.twitter_access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True)
    try:
        api.verify_credentials()
    except Exception as e:
        logger.error("Error creating APIv1.1", exc_info=True)
        raise e
    logger.info("Twitter API v1.1 created")
    return api


def create_twitter_api_v2(config):

    if (config.twitter_consumer_key is None or
        config.twitter_consumer_secret is None or
        config.twitter_access_token is None or
        config.twitter_access_token_secret is None or
        config.twitter_bearer_token is None ):
        raise Exception("CONSUMER_KEY and CONSUMER_SECRET and ACCESS_TOKEN and ACCESS_TOKEN_SECRET and BEARER_TOKEN env var must be configured.")

    client = tweepy.Client(consumer_key=config.twitter_consumer_key,
                       consumer_secret=config.twitter_consumer_secret,
                       access_token=config.twitter_access_token,
                       access_token_secret=config.twitter_access_token_secret,
                       bearer_token=config.twitter_bearer_token)
    try:
        client.get_me()
    except Exception as e:
        logger.error("Error creating APIv2", exc_info=True)
        raise e
    logger.info("Twitter API v2 created")

    return client


def create_mastodon_api(config):

    if (config.mastodon_client_id is None or
        config.mastodon_client_secret is None or
        config.mastodon_access_token is None or
        config.mastodon_api_base_url is None ):
        raise Exception("MASTODON_ID and MASTODON_SECRET and MASTODON_ACCESS_TOKEN and MASTODON_BASE_URL env var must be configured.")

    mastodon = Mastodon(
        client_id = "y7wTyKZeexNTiWhM-AVtNrBgxPj2CXR8J7KvFF-qP5Y",
        client_secret = "YvFoOfr3Bj0qfxWE4a3UcZ4aav8Mqq5b1OZLJ1Me3DQ",
        access_token = "Bckn-3YdzfGGnWhw8XaDebULZ1f3wyQHBFbqIXSCZYU",
        api_base_url = "https://social.sciences.re"
    )

    return mastodon


def get_wkpath():
    with os.popen("which wkhtmltoimage") as cmd:
        wkpath = cmd.read().rstrip('\n')
    return wkpath

class Config:

    configfile = os.path.dirname(os.path.abspath(__file__)) + "/config/config.json"

    def __init__(self):
        self.twitter_consumer_key = os.getenv("CONSUMER_KEY")
        self.twitter_consumer_secret = os.getenv("CONSUMER_SECRET")
        self.twitter_access_token = os.getenv("ACCESS_TOKEN")
        self.twitter_access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
        self.twitter_bearer_token = os.getenv("BEARER_TOKEN")
        self.piste_client_id = os.getenv("PISTE_CLIENT_ID")
        self.piste_client_secret = os.getenv("PISTE_CLIENT_SECRET")
        self.mastodon_client_id = os.getenv("MASTODON_ID")
        self.mastodon_client_secret = os.getenv("MASTODON_SECRET")
        self.mastodon_access_token = os.getenv("MASTODON_ACCESS_TOKEN")
        self.mastodon_api_base_url = os.getenv("MASTODON_BASE_URL")

        self.mdconfig_url = "https://raw.githubusercontent.com/cpesr/veilleesr-bot/master/botconfig.md"

        self.wk_path = get_wkpath()

        self.last_jorf = Config.now()
        self.last_recap = Config.now()
        self.itweet = 0
        self.lasttweetid = 0
        self.lasttootid = 0
        self.lastthreadid = 0
        self.retweets = {}

    @staticmethod
    def now():
        dtn = datetime.now()
        return {
          "year": int(dtn.strftime("%Y")),
          "month": int(dtn.strftime("%m")),
          "dayOfMonth": int(dtn.strftime("%d"))
        }

    @staticmethod
    def load():
        config = Config()
        try:
            with open(Config.configfile,"r") as sf:
                keyval = json.load(sf)
                for k in keyval:
                    setattr(config,k,keyval[k])
        except FileNotFoundError:
            config.save()

        return config

    def save(self):
        if not os.path.exists(os.path.dirname(self.configfile)):
            os.makedirs(os.path.dirname(self.configfile))
        with open(self.configfile,"w") as sf:
            json.dump(self, sf, indent=2, default=lambda o: o.__dict__)

    def reset_last_jorf(self):
        self.last_jorf = self.now()

    def reset_last_recap(self):
        self.last_recap = self.now()
