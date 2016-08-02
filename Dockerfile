FROM python:2.7.9

RUN apt-get -y update

RUN apt-get install -y python-shapely

RUN mkdir /code
WORKDIR /code

ADD . /code

RUN pip install --upgrade pip
RUN pip install -e git+https://github.com/terranodo/django-mapproxy@registry#egg=djmp
# Needed because an apparent bug where djmp is not linked properly.
RUN pip install src/djmp

RUN pip install -e /code

ONBUILD RUN python manage.py migrate --noinput
ONBUILD RUN python manage.py collectstatic --noinput
