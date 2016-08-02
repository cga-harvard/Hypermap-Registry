FROM python:2.7.9

RUN apt-get -y update

RUN apt-get install -y python-shapely

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY . /usr/src/app

RUN pip install --upgrade pip
RUN pip install -e git+https://github.com/terranodo/django-mapproxy@registry#egg=djmp
# Needed because an apparent bug where djmp is not linked properly.
RUN pip install src/djmp
RUN pip install -e /usr/src/app
