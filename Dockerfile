FROM python:3.8-slim-buster

COPY bots /bots/
COPY requirements.txt /tmp
RUN pip3 install -r /tmp/requirements.txt
# RUN apt-get update && apt-get install -y wkhtmltopdf

COPY wkhtmltox_0.12.5-1.stretch_amd64.deb /tmp
RUN apt update && apt install -y /tmp/wkhtmltox_0.12.5-1.stretch_amd64.deb

WORKDIR /bots
CMD ["python3", "veilleesr-bot.py"]
