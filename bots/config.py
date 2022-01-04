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

def create_api():
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True)
    try:
        api.verify_credentials()
    except Exception as e:
        logger.error("Error creating API", exc_info=True)
        raise e
    logger.info("API created")
    return api

class State:
    def __init__(self):
        self.last_jorf = State.now()
        self.last_recap = State.now()
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
        s = State()
        try:
            with open("state.json","r") as sf:
                state = json.load(sf)
                s.last_jorf = state['last_jorf']
                s.last_recap = state['last_recap']
                s.itweet = state['itweet']
                s.lasttweetid = state['lasttweetid']
        except FileNotFoundError:
            pass

        return s

    def save(self):
        with open("state.json","w") as sf:
            json.dump({
                "last_jorf":self.last_jorf,
                "last_recap":self.last_recap,
                "itweet":self.itweet,
                "lasttweetid":self.lasttweetid
                }, sf, indent=2)

    def reset_last_jorf(self):
        self.last_jorf = self.now()

    def reset_last_recap(self):
        self.last_recap = self.now()
