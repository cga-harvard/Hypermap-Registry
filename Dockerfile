FROM geonode/django
MAINTAINER Ariel Núñez<ariel@terranodo.io>

RUN pip uninstall -y pycsw
RUN pip install --upgrade git+git://github.com/geopython/pycsw.git@4fc1fc1eee3ac4b83d2862d311b20efb142e13bd#egg=pycsw
