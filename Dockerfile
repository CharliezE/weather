FROM python:3.11.9-slim-bullseye

RUN mkdir app
WORKDIR app

ADD . /app/

RUN pip install -r requirements.txt

ENV FLASK_RUN_PORT=5000

EXPOSE 5000

CMD python ./main.py
