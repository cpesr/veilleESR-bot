FROM python:3.8-slim-buster

COPY bots/config.py /bots/
COPY bots/mdconfig.py /bots/
COPY bots/veilleesr-bot.py /bots/
COPY requirements.txt /tmp
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /bots
CMD ["python3", "veilleesr-bot.py"]
