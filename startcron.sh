#! /usr/bin/sh

chmod 0644 /etc/cron.d/bot-cron
printenv >> /etc/environment
touch /var/log/cron.log
cron
tail -f /var/log/cron.log
