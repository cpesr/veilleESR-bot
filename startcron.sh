#! /bin/bash

date > /var/log/cron.log
python3 /bots/veilleesr-bot.py --createconfig
cron -f
