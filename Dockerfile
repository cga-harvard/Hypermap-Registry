FROM terranodo/django:development
MAINTAINER Ariel Núñez<ariel@terranodo.io>

pip install git+git://github.com/geopython/pycsw.git@master#egg=pycsw --upgrade
