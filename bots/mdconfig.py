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


from tweepy.streaming import urllib3
from os import path

def get_mdconfig(url):
    pm = urllib3.PoolManager()
    data = pm.request("GET", url, preload_content=False)

    botconfig = data.read().decode('utf-8').splitlines()
    config = {}
    tweets = []
    datamd = []
    l = []
    for bc in botconfig:
        if bc == "# Config": l = config
        elif bc == "# VeilleESR": l = tweets
        elif bc == "# DataESR": l = datamd
        elif len(bc) > 0:
            if (bc[0] == '-') :
                kv = bc[2:].split(":")
                config[kv[0]]=kv[1]
            else: l.append(bc)

    datatweets = []
    for dm in datamd:
        datatweets += get_datamd(dm)

    return({'config':config, 'tweets':tweets, 'datatweets':datatweets})

def md2img(line):
    end = line.find(".png")
    if end == -1: return None
    start = line.find('src="') + 5
    if start == -1: start = line.find("(") + 2
    return( line[start:end+4] )

def get_datamd(mdurl):
    pm = urllib3.PoolManager()
    data = pm.request("GET", mdurl, preload_content=False)
    datamd = data.read().decode('utf-8').splitlines()

    twtexte = "[#DataESR]"
    dtthread = ""
    twalt = ""
    twurl = ""
    url = ""

    datatweets = []
    for dm in datamd:
        dm = dm.strip(" ")
        if len(dm) > 0:
            if dm.startswith("- twtexte"): twtexte = dm[10:].strip(" ")
            elif dm.startswith("- twalt"): twalt = dm[8:].strip(" ")
            elif dm.startswith("- twurl"): twurl = dm[8:].strip(" <>")
            elif dm.startswith("- url"): url = dm[6:].strip(" <>")
            elif dm.startswith("#"):
                if dm.startswith("## "): dtthread = dm.lstrip('# ')
                dttexte = twtexte + '\n\n\U0001F4CA \U0001F4C9 ' + dm.lstrip('# ')
            else:
                dtimgurl = md2img(dm)
                if dtimgurl is not None:
                    dtimgurl = path.dirname(mdurl) + "/" + dtimgurl
                    datatweets.append({'text':dttexte, 'thread':dtthread, 'imgurl':dtimgurl, 'alt':twalt, 'twurl':twurl, 'url':url})

    return(datatweets)


def main():
    print(get_mdconfig("https://raw.githubusercontent.com/cpesr/veilleesr-bot/master/botconfig.md"))

if __name__ == "__main__":
    main()
