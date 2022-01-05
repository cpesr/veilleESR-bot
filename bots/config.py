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
import logging
import os
import json
from datetime import datetime

logger = logging.getLogger()

def create_twitter_api(config):

    if (config.twitter_consumer_key is None or
        config.twitter_consumer_key is None or
        config.twitter_access_token is None or
        config.twitter_access_token_secret is None ):
        raise Exception("CONSUMER_KEY and CONSUMER_SECRET and ACCESS_TOKEN and ACCESS_TOKEN_SECRET env var must be configured.")


    auth = tweepy.OAuthHandler(config.twitter_consumer_key, config.twitter_consumer_secret)
    auth.set_access_token(config.twitter_access_token, config.twitter_access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True)
    try:
        api.verify_credentials()
    except Exception as e:
        logger.error("Error creating API", exc_info=True)
        raise e
    logger.info("API created")
    return api

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
        self.piste_client_id = os.getenv("PISTE_CLIENT_ID")
        self.piste_client_secret = os.getenv("PISTE_CLIENT_SECRET")

        self.mdconfig_url = "https://raw.githubusercontent.com/cpesr/veilleesr-bot/master/botconfig.md"

        self.wk_path = get_wkpath()

        self.last_jorf = Config.now()
        self.last_recap = Config.now()
        self.itweet = 0
        self.lasttweetid = 0

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
