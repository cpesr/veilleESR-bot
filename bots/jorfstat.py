import jorf
import config
from datetime import datetime, timedelta
import argparse

def dtformat(dt):
    return {"year": dt.year, "month": dt.month, "dayOfMonth": dt.day}


parser = argparse.ArgumentParser(description='Gratteur de stats à propos des JORF')
parser.add_argument('date', type=str, nargs='?', default=datetime.now().strftime("%Y-%m-%d"),
                    help="Date de début au format 2020-12-31")
parser.add_argument('--noheader', dest='noheader', action="store_const", const=True, default=False,
                    help="N'affiche pas le header")

args = parser.parse_args()

conf = config.Config.load()
jorf = jorf.JORF(conf)

d = datetime.strptime(args.date,"%Y-%m-%d")

if not args.noheader:
    print("Date,JO,JOID,Nature,Titre", flush=True)

while d.year != 1989:
    jo = jorf.piste_req("jorfCont",{"start":dtformat(d), "end":dtformat(d), "pageNumber": 1, "pageSize": 100})
    try:
        titre=jo['items'][0]['joCont']['titre']
        id =jo['items'][0]['joCont']['id']
        esr = jorf.esr_lookup(jo['items'][0]['joCont']['structure']['tms'][0])
    except (IndexError,TypeError):
        titre="NA"
        id="NA"
        esr = []
    for e in esr:
        print(d.strftime("%Y-%m-%d")+','+titre+','+id+','+e['nature']+',"'+e['titre']+'"')
    d = d - timedelta(days=1)



d = datetime.strptime("2012-10-15","%Y-%m-%d")
jo = jorf.piste_req("jorfCont",{"start":dtformat(d), "end":dtformat(d), "pageNumber": 1, "pageSize": 100})
