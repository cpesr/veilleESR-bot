#! /bin/bash

echo "Start" > /var/log/cron.log
python3 /bots/veilleesr-bot.py --createconfig
cron -f
