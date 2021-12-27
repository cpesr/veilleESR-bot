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
import json
import os
import imgkit
from io import BytesIO

class JORF:
    def __init__(self):
        self.pm = tweepy.streaming.urllib3.PoolManager()
        self.get_access_token()
        self.jorf = None
        self.sommaire = None
        self.esr = None

        self.css = "jorf.css"


    def get_access_token(self):
        client_id = os.getenv("PISTE_CLIENT_ID")
        client_secret = os.getenv("PISTE_CLIENT_SECRET")
        if (client_id is None or client_secret is None):
            raise Exception("PISTE_CLIENT_ID and PISTE_CLIENT_SECRET env var must be set.")

        req = self.pm.request(
            "POST",
            "https://oauth.piste.gouv.fr/api/oauth/token/api/oauth/token",
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'},
            body = "grant_type=client_credentials&client_id="+client_id+"&client_secret="+client_secret+"&scope=openid")
        self.access_token = json.loads(req.data)['access_token']
        return self.access_token

    def piste_req(self,controller,params):
        req = self.pm.request(
            "POST",
            "https://api.piste.gouv.fr/dila/legifrance-beta/lf-engine-app/consult/"+controller,
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': 'Bearer '+self.access_token },
            body = json.dumps(params))
        return json.loads(req.data)

    @staticmethod
    def jorf2url(jorf):
        return "https://www.legifrance.gouv.fr/jorf" + jorf['containers'][0]['idEli'][4:]

    @staticmethod
    def texte2url(texte):
        return "https://www.legifrance.gouv.fr/jorf/id/"+texte['id']

    def get_jorf(self):
        if self.jorf is None:
            self.jorf = self.piste_req("lastNJo",{"nbElement":1})
        return self.jorf

    def get_sommaire(self):
        if self.sommaire is None:
            self.sommaire = self.piste_req("jorfCont",{"id":self.get_jorf()['containers'][0]['id'], "pageNumber": 1, "pageSize": 3})
        return self.sommaire


    @staticmethod
    def esr_detect(string, keywords=["echerche", "seignement supérieur"]):
        return any([k in string for k in keywords])

    @staticmethod
    def esr_lookup(jorf):
        res = []
        #print('-' * jorf['niv'],  end = '')
        #print(jorf['titre'])
        if JORF.esr_detect(jorf['titre']): res += jorf['liensTxt']
        else:
            for txt in jorf['liensTxt']:
                if JORF.esr_detect(txt['titre']): res += [ txt ]
        for item in jorf['tms']:
            res += JORF.esr_lookup(item)
        return res

    def get_esr(self):
        if self.esr is None:
            self.esr = self.esr_lookup(self.get_sommaire()['items'][0]['joCont']['structure']['tms'][0])
        return self.esr

    def get_last_JO_id(self):
        return self.get_jorf()['containers'][0]['id']

    def get_text(self, id):
        return self.piste_req("jorf",{"textCid":id})

    def sommaire2html(self):
        html = '<div>'
        html += '<H1>'+self.get_sommaire()['items'][0]['joCont']['titre']+"</H1>"
        html += '<H2>Sélection ESR</H2>'
        html += "<ul>"
        for texte in self.get_esr():
            html += "<li>"+texte['titre']+"</li>"
        html += "</ul>"
        html += '</div>'
        return html

    @staticmethod
    def cont2html(cont):
        html = '<div>'
        html += "<H1>"+cont['title']+"</H1>"
        for article in cont['articles']:
            if article['num'] is not None:
                html += "<H2>Article "+article['num']+"</H2>"
            html += article['content']
        html += '</div>'
        return html

    def get_jotweets(self, write_img = False):
        jotext = "[#VeilleESR #JORF] Publications au Journal Officiel concernant l'#ESR\n\U0001F5DE "+self.get_sommaire()['items'][0]['joCont']['titre']+" \n\n"+self.jorf2url(self.jorf)
        if write_img:
            imgkit.from_string(self.sommaire2html(), self.get_last_JO_id()+'.png', css=self.css)
            joimg = self.get_last_JO_id()+'.png'
        else:
            joimg = BytesIO(imgkit.from_string(self.sommaire2html(), False, css=self.css)) #self.get_last_JO_id()+'.png')

        jotweets = [ {'id':self.get_last_JO_id(), 'text':jotext, 'img':joimg} ]

        for texte in self.get_esr():
            txt = texte['titre'] if len(texte['titre']) <= 220 else texte['titre'][:220]+"..."
            jotext = "[#VeilleESR #JORF] "+txt+"\n\n\U0001F4F0 "+self.texte2url(texte)

            cont = self.piste_req('jorf',{'textCid':texte['id']})
            html = self.cont2html(cont)
            if write_img:
                imgkit.from_string(html, texte['id']+'.png', css=self.css)
                joimg = texte['id']+'.png'
            else:
                joimg = BytesIO(imgkit.from_string(html,False, css=self.css)) #texte['id']+'.png')


            jotweets += [ {'id':texte['id'], 'text':jotext, 'img':joimg} ]

        return jotweets

def main():
    jorf = JORF()
    print(jorf.get_last_JO_id())
    print(jorf.get_jotweets(write_img=True))


if __name__ == "__main__":
    main()
