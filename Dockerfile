FROM terranodo/django:development
MAINTAINER Ariel Núñez<ariel@terranodo.io>

RUN pip install git+git://github.com/geopython/pycsw.git@master#egg=pycsw --upgrade
