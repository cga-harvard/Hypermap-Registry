FROM terranodo/django:development
MAINTAINER Ariel Núñez<ariel@terranodo.io>

RUN pip uninstall -y pycsw
RUN pip uninstall -y django-registry

RUN pip install https://github.com/geopython/pycsw/archive/master.zip
