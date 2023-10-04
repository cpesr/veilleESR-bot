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


def get_wkpath():
    with os.popen("which wkhtmltoimage") as cmd:
        wkpath = cmd.read().rstrip('\n')
    return wkpath

class Config:

    configfile = os.path.dirname(os.path.abspath(__file__)) + "/config/config.json"

    def __init__(self):
        self.config = {
            'mdconfig_url': "https://raw.githubusercontent.com/cpesr/veilleesr-bot/master/botconfig.md",
            'wk_path': get_wkpath(),
            'last_veille_bsky_id': "",
            'last_veille_masto_id': "",
            'last_jorf': Config.now(),
            'last_recap': Config.now(),
            'ipost': 0 }

    def get(self,key):
        try:
            return(self.config[key])
        except KeyError:
            self.config[key] = os.environ.get(key.upper())
            if not self.config[key]:
                raise KeyError(key.upper()+" env var must be set")
            return(self.config[key])

    def set(self,key,val):
        self.config[key] = val
        return val


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
                config.config = json.load(sf)
                # keyval = json.load(sf)
                # for k in keyval:
                #     setattr(config,k,keyval[k])
        except FileNotFoundError:
            config.save()

        return config

    def save(self):
        if not os.path.exists(os.path.dirname(self.configfile)):
            os.makedirs(os.path.dirname(self.configfile))
        with open(self.configfile,"w") as sf:
            json.dump(self.config,sf,indent=2)
            #json.dump(self, sf, indent=2, default=lambda o: o.__dict__)

    def reset_last_jorf(self):
        self.set("last_jorf", self.now())

    def reset_last_recap(self):
        self.set("last_recap", self.now())

if __name__ == "__main__":
    config = Config.load()
    print(config.get("TWITTERJG_CONSUMER_KEY"))
