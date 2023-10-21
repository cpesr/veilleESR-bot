import requests
import datetime
import os
import unittest
import mimetypes
import json
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger()

class APIBluesky():
    def __init__(self, username, password):

        self.ATP_HOST = "https://bsky.social"
        self.ATP_AUTH_TOKEN = ""
        self.DID = ""
        self.USERNAME = username
        self.PASSWORD = password
        self.followersDid = None

        resp = requests.post(
            self.ATP_HOST + "/xrpc/com.atproto.server.createSession",
            json={"identifier": self.USERNAME, "password": self.PASSWORD}
        )

        self.ATP_AUTH_TOKEN = resp.json().get('accessJwt')
        if self.ATP_AUTH_TOKEN == None:
            rc = json.loads(resp.content)
            if rc["error"] == "RateLimitExceeded":
                raise ValueError("Rate limit exceeded: "+str(resp.headers))

            raise ValueError("No access token because"+rc["message"]+", is your password wrong? Do     export BSKY_PASSWORD='yourpassword'")

        self.RateLimitRemaining = resp.headers['RateLimit-Remaining']

        self.DID = resp.json().get("did")
        # TODO DIDs expire shortly and need to be refreshed for any long-lived sessions

    def reinit(self):
        """Check if the session needs to be refreshed, and refresh if so."""
        # TODO
        # if a request failed, use refreshJWT
        resp = self.get_profile("klatz.co")

        if resp.status_code == 200:
            # yay!
            # do nothing lol
            pass
        else: # re-init
            # what is the endpoint
            pass


    def doOnPost(self, action, post):
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        timestamp = timestamp.isoformat().replace('+00:00', 'Z')

        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}

        data = {
            "collection": "app.bsky.feed."+action,
            "repo": "{}".format(self.DID),
            "record": {
                "subject": {
                    "uri":post['uri'],
                    "cid":post['cid']
                },
                "createdAt": timestamp,
                "$type": "app.bsky.feed."+action
            }
        }

        resp = requests.post(
            self.ATP_HOST + "/xrpc/com.atproto.repo.createRecord",
            json=data,
            headers=headers
        )

        return resp

    def repost(self, post):
        self.doOnPost("repost", post)

    def like(self, post):
        self.doOnPost("like", post)

    def resolveHandle(self, username):
        """Get the DID given a username, aka getDid."""
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        resp = requests.get(
            self.ATP_HOST + "/xrpc/com.atproto.identity.resolveHandle?handle={}".format(username),
            headers=headers
        )
        return resp

    def getSkyline(self,n = 10):
        """Fetch the logged in account's following timeline ("skyline")."""
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        resp = requests.get(
            self.ATP_HOST + "/xrpc/app.bsky.feed.getTimeline?limit={}".format(n),
            headers=headers
        )
        return resp

    def getPostByUrl(self, url):
        """Get a post's HTTP response data when given the URL."""
        # https://staging.bsky.app/profile/shinyakato.dev/post/3ju777mfnfv2j
        "https://bsky.social/xrpc/app.bsky.feed.getPostThread?uri=at%3A%2F%2Fdid%3Aplc%3Ascx5mrfxxrqlfzkjcpbt3xfr%2Fapp.bsky.feed.post%2F3jszsrnruws27A"
        "at://did:plc:scx5mrfxxrqlfzkjcpbt3xfr/app.bsky.feed.post/3jszsrnruws27"
        "https://staging.bsky.app/profile/naia.bsky.social/post/3jszsrnruws27"


        # getPosts
        # https://bsky.social/xrpc/app.bsky.feed.getPosts?uris=at://did:plc:o2hywbrivbyxugiukoexum57/app.bsky.feed.post/3jua5rlgrq42p

        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}

        username_of_person_in_link = url.split('/')[-3]
        if not "did:plc" in username_of_person_in_link:
            did_of_person_in_link = self.resolveHandle(username_of_person_in_link).json().get('did')
        else:
            did_of_person_in_link = username_of_person_in_link

        url_identifier = url.split('/')[-1] # the random stuff at the end, better hope there's no query params

        uri = "at://{}/app.bsky.feed.post/{}".format(did_of_person_in_link, url_identifier)

        resp = requests.get(
            self.ATP_HOST + "/xrpc/app.bsky.feed.getPosts?uris={}".format(uri),
            headers=headers
        )

        return resp

    def uploadImage(self, image):
        if 'url' in image:
            resp = requests.get(image['url'])
            resp_blob = self.uploadBlob(resp.content, resp.headers['Content-Type'])
        elif 'data' in image:
            resp_blob = self.uploadBlob(image['data'], image['content_type'])
        else:
            content_type = mimetypes.guess_type(image['path'])[0]
            with open(image['path']) as f:
                resp_blob = self.uploadBlob(f.read(), content_type)

        return resp_blob

    def uploadBlob(self, stream, content_type=None, timeout=10, attempts=5):
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN, "Content-Type": content_type}

        while attempts > 0:
            try:
                resp = requests.post(
                    self.ATP_HOST + "/xrpc/com.atproto.repo.uploadBlob",
                    data=stream,
                    headers=headers,
                    timeout=timeout)
                return resp
            except requests.exceptions.ReadTimeout:
                attempts -= 1

    def postVPost(self, vpost, reply_to=None):
        """Post a post."""

        timestamp = datetime.datetime.now(datetime.timezone.utc)
        timestamp = timestamp.isoformat().replace('+00:00', 'Z')

        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}

        text = vpost['text']
        cardfacet = []
        #text = text.replace(vpost['card']['url'],"")

        data = {
            "collection": "app.bsky.feed.post",
            "$type": "app.bsky.feed.post",
            "repo": "{}".format(self.DID),
            "record": {
                "$type": "app.bsky.feed.post",
                "createdAt": timestamp,
                "text": text
            }
        }

        if 'images' in vpost and len(vpost['images']) > 0:
            images = []
            for image in vpost['images']:
                #print("Upload "+ip)
                try:
                    image_resp = self.uploadImage(image)
                    image_resp.raise_for_status()
                    blob = image_resp.json().get('blob')
                    if blob['size'] > 1000000:
                        raise Exception(f"image file size too large. 1000000 bytes maximum, got: {blob['size']}")

                    images.append({
                        "alt": image['alt'],
                        "image": blob
                    })
                except Exception as e:
                    logger.warning("Error while uploading image on bluesky: "+str(e))
                    pass

            if len(images) > 0:
                data['record']['embed'] = {}
                data["record"]["embed"]["$type"] = "app.bsky.embed.images"
                data['record']["embed"]['images'] = images


        if 'embed' not in data['record']:
            # Si pas d'images, alors on met la carte
            if 'card' in vpost and vpost['card']:
                data['record']['embed'] = {
                    "$type": "app.bsky.embed.external",
                    "external": {
                        "uri": vpost['card']['url'],
                        "title": vpost['card']['title'],
                        "description": vpost['card']['description']
                    }
                }
                try:
                    resp_blob = self.uploadImage(vpost['card']['image'])
                    data['record']['embed']['external']['thumb']: resp_blob.json()["blob"]
                except:
                    pass

            elif 'cardurl' in vpost:
                data['record']['embed'] = self.fetch_embed_url_card(vpost['cardurl'])
        else:
            # Si des images, alors on convertit la carte en lien
            if 'cardurl' in vpost:
                text = text+" "+vpost['cardurl']
                start = bytes(text,encoding='utf-8').find(bytes(vpost['cardurl'],encoding='utf-8'))
                end = start + len(bytes(vpost['cardurl'],encoding='utf-8'))
                data['record']['text'] = text
                data['record']['facets'] = [ {'index': { 'byteStart':start, 'byteEnd':end},
                        'features': [ {'uri': vpost['cardurl'], '$type': 'app.bsky.richtext.facet#link'} ] } ]


        if reply_to:
            data['record']['reply'] = reply_to

        if 'facets' in vpost :
            if 'facets' not in data['record']: data['record']['facets'] = []
            data['record']['facets'] += vpost['facets']

        # print(data)
        resp = requests.post(
            self.ATP_HOST + "/xrpc/com.atproto.repo.createRecord",
            json=data,
            headers=headers
        )
        resp.raise_for_status()
        return resp

    def postVThread(self, vthread):
        rt = None
        for vpost in vthread:
            # img = vpost.pop('images')
            # print(json.dumps(vpost,indent=2))
            resp = self.postVPost(vpost, reply_to = rt)
            post = json.loads(resp.content)
            if not rt:
                root = {'uri':post['uri'], 'cid':post['cid']}
            parent = {'uri':post['uri'], 'cid':post['cid']}
            rt = {'root':root, 'parent':parent}


    def importVPost(self, vpost):
        text = "[#VeilleESR] "+vpost['card']['title']+"\n\nVia "+vpost['url']
        start = bytes(text,encoding='utf-8').find(bytes(vpost['url'],encoding='utf-8'))
        end = start + len(bytes(vpost['url'],encoding='utf-8'))
        ipost = {
            'text':text,
            'card':vpost['card'],
            'images':[],
            'facets': [ {'index': { 'byteStart':start, 'byteEnd':end},
                'features': [ {'uri': vpost['url'], '$type': 'app.bsky.richtext.facet#link'} ] } ]
        }
        self.postVPost(ipost)



    def deletePost(self, did,rkey):
        # rkey: post slug
        # i.e. /profile/foo.bsky.social/post/AAAA
        # rkey is AAAA
        data = {"collection":"app.bsky.feed.post","repo":"did:plc:{}".format(did),"rkey":"{}".format(rkey)}
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        resp = requests.post(
            self.ATP_HOST + "/xrpc/com.atproto.repo.deleteRecord",
            json = data,
            headers=headers
        )
        return resp

    def getArchive(self, did_of_car_to_fetch=None, save_to_disk_path=None):
        """Get a .car file containing all posts.

        TODO is there a putRepo?
        TODO save to file
        TODO specify user
        """

        if did_of_car_to_fetch == None:
            did_of_car_to_fetch = self.DID

        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}

        resp = requests.get(
            self.ATP_HOST + "/xrpc/com.atproto.sync.getRepo?did={}".format(did_of_car_to_fetch),
            headers = headers
        )

        if save_to_disk_path:
            pass

        return resp

    def getLatestPost(self, accountname):
        """Return the most recent Post from the specified account."""
        return self.getLatestNPosts(accountname, 1)

    def getLatestNPosts(self, username, n=5):
        """Return the most recent n Posts from the specified account."""
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        resp = requests.get(
            self.ATP_HOST + "/xrpc/app.bsky.feed.getAuthorFeed?actor={}&limit={}".format(username, n),
            headers = headers
        )

        return resp

    # [[API Design]] TODO one implementation should be highly ergonomic (comfy 2 use) and the other should just closely mirror the API's exact behavior?
    # idk if im super happy about returning requests, either, i kinda want tuples where the primary object u get back is whatever ergonomic thing you expect
    # and then you can dive into that and ask for the request. probably this means writing a class to encapsulate each of the
    # API actions, populating the class in the implementations, and making the top-level api as pretty as possible
    # ideally atproto lib contains meaty close-to-the-api and atprototools is a layer on top that focuses on ergonomics?
    def follow(self, username=None, did=None):
        """Follow the user with the given username or DID."""

        if username:
            did = self.resolveHandle(username).json().get("did")

        if not self.followersDid:
            self.followersDid = self.getFollowersDid()
        if did in self.followersDid: return None


        if not did:
            # TODO better error in resolveHandle
            raise ValueError("Failed; please pass a username or did of the person you want to follow (maybe the account doesn't exist?)")

        timestamp = datetime.datetime.now(datetime.timezone.utc)
        timestamp = timestamp.isoformat().replace('+00:00', 'Z')

        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}

        data = {
            "collection": "app.bsky.graph.follow",
            "repo": "{}".format(self.DID),
            "record": {
                "subject": did,
                "createdAt": timestamp,
                "$type": "app.bsky.graph.follow"
            }
        }

        resp = requests.post(
            self.ATP_HOST + "/xrpc/com.atproto.repo.createRecord",
            json=data,
            headers=headers
        )

        return resp

    def getFollowersDid(self):
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        resp = requests.get(self.ATP_HOST + "/xrpc/app.bsky.graph.getFollows", params={'actor':"cpesr.fr"}, headers=headers)
        resp.raise_for_status()
        jresp = json.loads(resp.content)
        followersDid = [ f['did'] for f in jresp['follows'] ]
        return followersDid

    def unfollow(self):
        # TODO lots of code re-use. package everything into a API_ACTION class.
        raise NotImplementedError

    def get_profile(self, username):
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}

        # TODO did / username check, it should just work regardless of which it is

        resp = requests.get(
            self.ATP_HOST + "/xrpc/app.bsky.actor.getProfile?actor={}".format(username),
            headers=headers
        )

        return resp

    def fetch_embed_url_card(self, url: str):
        # the required fields for every embed card
        card = {
            "uri": url,
            "title": "",
            "description": "",
        }

        # fetch the HTML
        headers = {
            'user-agent':"Mozilla/5.0 ...",
            'accept': '"text/html,application...',
            'referer': 'https://...',
        }
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # parse out the "og:title" and "og:description" HTML meta tags
            title_tag = soup.find("meta", property="og:title")
            if title_tag:
                card["title"] = title_tag["content"]

            description_tag = soup.find("meta", property="og:description")
            if description_tag:
                card["description"] = description_tag["content"]

            # if there is an "og:image" HTML meta tag, fetch and upload that image
            image_tag = soup.find("meta", property="og:image")
            if image_tag:
                img_url = image_tag["content"]

                # naively turn a "relative" URL (just a path) into a full URL, if needed
                if "://" not in img_url:
                    img_url = url + img_url
                resp = requests.get(img_url, headers=headers)
                resp.raise_for_status()

                while True:
                    try:
                        mimetype = mimetypes.guess_type(img_url)[0]
                        blob_resp = requests.post(
                            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
                            headers={
                                "Content-Type": mimetype,
                                "Authorization": "Bearer " + self.ATP_AUTH_TOKEN,
                            },
                            data=resp.content,
                            timeout=2
                        )
                        break
                    except requests.exceptions.ReadTimeout:
                        logging.warning("Upload blob timeout... waiting {} seconds".format(waittime))
                        time.sleep(2)
                        pass
                try:
                    blob_resp.raise_for_status()
                    if blob_resp.json()["blob"]['size'] < 976560:
                        card["thumb"] = blob_resp.json()["blob"]
                except:
                    pass
        except:
            pass
        return {
            "$type": "app.bsky.embed.external",
            "external": card,
        }

    def getFeed(self, aturl):

        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        resp = requests.get(self.ATP_HOST + "/xrpc/app.bsky.feed.getFeed", params={'feed':aturl}, headers=headers)
        resp.raise_for_status()

        return(json.loads(resp.content)['feed'])

        #for f in feed['feed']: print(f['post']['record']['createdAt'])

    def getVPost(self, post):
        btext = bytes(post['record']['text'],encoding="utf-8")
        if 'facets' in post['record']:
            for f in post['record']['facets']:
                if f['features'][0]['$type'] == "app.bsky.richtext.facet#link":
                    buri = bytes(f['features'][0]['uri'],encoding="utf-8")
                    btext = btext[0:f['index']['byteStart']] + buri + btext[f['index']['byteEnd']:]

                    #text = text.replace(uri[8:37]+"...",uri)

        vpost = {
            'text': btext.decode(),
            'card': None,
            'author': post['author']['handle'],
            'id': post['uri'],
            'url': self.getPostURL(post),
            'images': [],
            'platform': "bluesky",
            'raw': post }

        try:
            vpost['card'] = {
                'url': post['embed']['external']['uri'],
                'title': post['embed']['external']['title'],
                'description': post['embed']['external']['description'] }
            vpost['card']['image'] = { 'url':post['embed']['external']['thumb'] }
        except KeyError:
            pass

        try:
            vpost['images'] = [ { 'url':image['fullsize'],'alt':image['alt']} for image in post['embed']['images'] ]
        except KeyError:
            pass

        return vpost

    def getPostURL(self, post):
        return post['uri'].replace("at://","https://bsky.app/profile/").replace("app.bsky.feed.post","post")

    def getVeille(self, last_uri = ""):
        followersDid = self.getFollowersDid()
        feed = self.getFeed('at://did:plc:ido6hzdau32ltop6fdhk7s7t/app.bsky.feed.generator/aaak6srraeqxm')

        veille = []
        for post in feed:
            post = post['post']
            if post['uri'] == last_uri: break
            vpost = self.getVPost(post)
            if vpost['author'] != "cpesr.fr":
                self.like(post)
                self.repost(post)
                self.follow(did=vpost['raw']['author']['did'])
                veille.append(vpost)

        return veille


    def getPostThread(self, aturl, depth=15):

        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        resp = requests.get(self.ATP_HOST + "/xrpc/app.bsky.feed.getPostThread", params={'uri':aturl, 'depth':depth}, headers=headers)
        resp.raise_for_status()

        return(json.loads(resp.content)['thread'])

    def getVThread(self, post):
        thread = self.getPostThread(post['uri'])
        did = thread['post']['author']['did']
        vthread = []
        while True:
            try:
                vthread.append(self.getVPost(thread['post']))
                thread = thread['replies'][0]
                if thread['post']['author']['did'] != did: break
            except IndexError:
                break
        return vthread

#'at://did:plc:mf3wkwt3y7gj32dbunijoefg/app.bsky.feed.post/3kahszi5j7k2i'

def register(user, password, invcode, email):
    data = {
        "email": email,
        "handle": user + ".bsky.social",
        "inviteCode": invcode,
        "password": password,
    }

    resp = requests.post(
        # don't use self.ATP_HOST here because you can't instantiate a session if you haven't registered an account yet
        "https://bsky.social/xrpc/com.atproto.server.createAccount",
        json = data,
    )

    return resp


if __name__ == "__main__":
    # This code will only be executed if the script is run directly
    # login(os.environ.get("BSKY_USERNAME"), os.environ.get("BSKY_PASSWORD"))
    apibsky = APIBluesky(os.environ.get("BSKY_USERNAME"), os.environ.get("BSKY_PASSWORD"))
    f = apibsky.getFollowersDid()
    print(f)

    # headers = {"Authorization": "Bearer " + apibsky.ATP_AUTH_TOKEN}
    # resp = requests.get(apibsky.ATP_HOST + "/xrpc/app.bsky.graph.getFollows", params={'actor':"cpesr.bsky.social"}, headers=headers)
