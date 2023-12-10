import requests
import datetime
import os
from collections import OrderedDict
import operator
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
        self.followsDid = None
        self.config = self.loadConfig()

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

    def loadConfig(self):
        configfile = os.path.dirname(os.path.abspath(__file__)) + "/config/bsconfig.json"

        with open(configfile) as f:
            self.config = json.load(f)
        return self.config

    def saveConfig(self):
        with open("config/bsconfig.json","w") as f:
            f.write(json.dumps(self.config, indent=4))


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

        username_of_person_in_link = url.split('/')[-3]
        if not "did:plc" in username_of_person_in_link:
            did_of_person_in_link = self.resolveHandle(username_of_person_in_link).json().get('did')
        else:
            did_of_person_in_link = username_of_person_in_link

        url_identifier = url.split('/')[-1] # the random stuff at the end, better hope there's no query params

        return self.getPost(did_of_person_in_link, url_identifier)


    def getPost(self, did, purl):
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        uri = "at://{}/app.bsky.feed.post/{}".format(did, purl)

        resp = requests.get(
            self.ATP_HOST + "/xrpc/app.bsky.feed.getPosts?uris={}".format(uri),
            headers=headers
        )
        resp.raise_for_status()

        return json.loads(resp.content)['posts'][0]

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
                if 'thumb' in vpost['card']:
                    data['record']['embed']['external']['thumb'] = vpost['card']['thumb']
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

        if 'embed' not in data['record'] and 'quote' in vpost:
            # Si pas d'images ni de card, alors on met le quote
            data['record']['embed'] = {
                "$type": "app.bsky.embed.record",
                "record": vpost['quote']
            }

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
        # print(resp.content)
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

    def follow(self, username=None, did=None):
        """Follow the user with the given username or DID."""

        if username:
            did = self.resolveHandle(username).json().get("did")

        if not self.followsDid:
            self.followsDid = self.getFollowsDid()
        if did in self.followsDid: return None


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

    def getFollows(self):
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        follows = []
        nf = 100
        cursor = None
        while nf == 100:
            resp = requests.get(self.ATP_HOST + "/xrpc/app.bsky.graph.getFollows", params={'actor':"cpesr.fr", 'limit':100, 'cursor':cursor}, headers=headers)
            resp.raise_for_status()
            jresp = json.loads(resp.content)
            follows += jresp['follows']
            nf = len(jresp['follows'])
            cursor = jresp['cursor']

        return(follows)

    def getFollowsDid(self):
        follows = self.getFollows()
        followsDid = [ f['did'] for f in follows ]
        return followsDid

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
        resp = requests.get(self.ATP_HOST + "/xrpc/app.bsky.feed.getFeed", params={'feed':aturl,'limit':100}, headers=headers)
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

        #print(post)
        vpost = {
            'text': btext.decode(),
            'card': None,
            'author': post['author']['handle'],
            'author_name': post['author']['displayName'] if 'displayName' in post['author'] else post['author']['handle'],
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


    def getTops(self, last_uri="", toplength = 5):
        feed = self.getFeed('at://did:plc:ido6hzdau32ltop6fdhk7s7t/app.bsky.feed.generator/aaak6srraeqxm')
        posts = []
        hello = []
        helpposts = []
        nposts = dict()

        for post in feed:
            if post['post']['uri'] == last_uri: break

            post = post['post']
            handle = post['author']['handle']


            posts.append({
                'record':{'uri':post['uri'], 'cid':post['cid']},
                'popularity':post['replyCount'] + post['repostCount'] + post['likeCount']
                })

            if handle == "cpesr.fr": continue

            if "HelloESR" in post['record']['text']:
                hello.append({'handle':handle, 'did':post['author']['did']})

            if "HelpESR" in post['record']['text']:
                helpposts.append({'record':{'uri':post['uri'], 'cid':post['cid']}})

            try:
                nposts[handle]['nposts'] += 1
            except:
                nposts[handle] = {'handle':handle, 'did':post['author']['did'], 'nposts':1}


        nposts = sorted(nposts.values(), key=operator.itemgetter('nposts'), reverse=True)[0:toplength]
        popposts = sorted(posts, key=operator.itemgetter('popularity'), reverse=True)[0:toplength]

        return {'hello':hello,'nposts':nposts,'popposts':popposts, 'helpposts':helpposts, 'last_uri':feed[0]['post']['uri']}

    def getNewCertifieds(self):
        follows = self.getFollows()
        certifieds = [ {'handle':f['handle'],'did':f['did']} for f in follows if "cpesr.fr" in f['handle'] ]
        newcertifieds = [ c for c in certifieds if c not in self.config['certifieds'] ]

        self.config['certifieds'] = certifieds

        return(newcertifieds)

    def sliceHandles(self, authors, intro="", maxlength=290):
        slices=[]
        s=intro
        facets=[]
        end = 0
        for author in authors:
            if end+len(author['handle'])+4>maxlength:
                slices.append({'text':s,'facets':facets})
                s=intro
                facets=[]
            start = len(bytes(s,encoding='utf-8'))
            s+="@"+author['handle']+"\n"
            end = len(bytes(s,encoding='utf-8'))-1
            facets.append({'index': { 'byteStart':start, 'byteEnd':end},
             'features': [ {'did':author['did'], "$type":"app.bsky.richtext.facet#mention"} ] })
        if s != intro: slices.append({'text':s,'facets':facets})
        return slices


    def postRecap(self, last_uri=""):
        # r = apibsky.uploadImage({'url':"https://cpesr.fr/wp-content/uploads/2020/01/ahmed-badawy-R4-DtoeKcHA-unsplash-scaled-e1606055582140.jpg"})
        card = {
            'title': "Feed #VeilleESR",
            'description': "Le feed des praticiennes et praticiens de l'ESR",
            'url': "https://bsky.app/profile/did:plc:ido6hzdau32ltop6fdhk7s7t/feed/aaak6srraeqxm",
            'thumb': {"$type":"blob","ref":{"$link":"bafkreibnqtbszx45rtwckdsfdscup3bg2kuhsc6ysd5qhzmrcpfnvnbdfe"},"mimeType":"image/jpeg","size":306895} }

        tops = self.getTops(last_uri)
        newcertifieds = self.getNewCertifieds()

        vthread = []
        for npost in self.sliceHandles(tops['nposts'],intro=
            "📣 Recap de la semaine #VeilleESR \n\n"+
            "🫶 Contributions les plus actives :\n"):
            vthread.append({'text': npost['text'],
                            'facets': npost['facets'],
                            'card':card})

        for poppost in tops['popposts']:
            vthread.append({'text': "🏅 Posts les plus populaires\n",
                        'quote': poppost['record']})

        for helppost in tops['helpposts']:
            vthread.append({'text': "💬 Demande d'aide #HelpESR\n",
                        'quote': helppost['record']})

        for hello in self.sliceHandles(tops['hello'],intro="👋 Bienvenue à :\n"):
            vthread.append({'text': hello['text'],
                            'facets': hello['facets']})

        for certifs in self.sliceHandles(newcertifieds,intro="🧑‍🏫 Nouvelles certifications :\n"):
            vthread.append({'text': certifs['text'],
                            'facets': certifs['facets']})

        self.config['topposts'] += tops['popposts']
        self.saveConfig()

        #return(vthread)

        self.postVThread(vthread)

        return tops



    def getPostThread(self, aturl, depth=1):
        headers = {"Authorization": "Bearer " + self.ATP_AUTH_TOKEN}
        resp = requests.get(self.ATP_HOST + "/xrpc/app.bsky.feed.getPostThread", params={'uri':aturl, 'depth':depth}, headers=headers)
        resp.raise_for_status()

        return json.loads(resp.content)['thread']


    def getVThread(self, post):
        did = post['author']['did']
        vthread = []

        while True:
            thread = self.getPostThread(post['uri'],depth=1)
            vthread.append(self.getVPost(thread['post']))

            if 'replies' not in thread: break

            post = None
            for replie in thread['replies']:
                if replie['post']['author']['did'] == did:
                    post = replie['post']
                    break

            if post is None : break

        return vthread


    def threadToTxt(self, url):
        post = self.getPostByUrl(url)
        txt = post['record']['text']+"\n\n"
        while 'reply' in post['record']:
            post = self.getPostByUrl(post['record']['reply']['parent']['uri'])
            txt = post['record']['text']+"\n\n"+txt
        return txt

    def getDNSZone(self):
        follows = self.getFollows()
        dnsz=""
        for f in follows:
            if 'handle.invalid' in f['handle']:
                handle = f['displayName']
                did = f['did']
                dnsz+='_atproto.'+handle+'          IN TXT    "did='+did+'"\n'
        dnsz+='\n'
        for f in follows:
            if 'cpesr.fr' in f['handle']:
                handle = f['handle'][0:-len('cpesr.fr')-1]
                did = f['did']
                dnsz+='_atproto.'+handle+'          IN TXT    "did='+did+'"\n'
        dnsz+='\n'
        for f in follows:
            if 'bsky.social' in f['handle']:
                handle = f['handle'][0:-12]
                did = f['did']
                dnsz+='_atproto.'+handle+'          IN TXT    "did='+did+'"\n'

        return(dnsz)




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
    # f = apibsky.getFollows()
    # print(f)
    # print(len(f))
    # dnsz = apibsky.getDNSZone()
    # print(dnsz)

    # lu = apibsky.getTops()
    # tops = apibsky.postRecap()
    # print(json.dumps(tops,indent=4))
    # print(json.dumps(tops["last_uri"],indent=4))

    # nc = apibsky.getNewCertifieds()
    # print(nc)

    # txt = apibsky.threadToTxt("https://bsky.app/profile/mmdejantee.bsky.social/post/3kfdk5tttlw27")
    # txt = apibsky.threadToTxt("https://bsky.app/profile/mmdejantee.bsky.social/post/3kfb5kil4hv2d")
    # txt = apibsky.threadToTxt("https://bsky.app/profile/mmdejantee.bsky.social/post/3kf6mw44j5v2d")
    # txt = apibsky.threadToTxt("https://bsky.app/profile/mmdejantee.bsky.social/post/3kffyhnue2t27")
    # print(txt)

    post = apibsky.getPostByUrl("https://bsky.app/profile/juliengossa.cpesr.fr/post/3kfxuwfqgto23")
    #print(json.dumps(post,indent=4))
    # thread = apibsky.getPostThread(post['uri'], depth=0)
    # print(json.dumps(thread,indent=4))

    vthread = apibsky.getVThread(post)
    for p in vthread: print(p['text']+"\n\n")


    # headers = {"Authorization": "Bearer " + apibsky.ATP_AUTH_TOKEN}
    # resp = requests.get(apibsky.ATP_HOST + "/xrpc/app.bsky.graph.getFollows", params={'actor':"cpesr.bsky.social"}, headers=headers)
