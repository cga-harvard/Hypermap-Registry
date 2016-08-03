FROM python:2.7.9

RUN apt-get -y update

RUN apt-get install -y python-shapely

RUN mkdir /code
WORKDIR /code

ADD . /code

RUN pip install -e /code
