FROM geonode/django
MAINTAINER Ariel Núñez<ariel@terranodo.io>

RUN pip uninstall -y pycsw
RUN pip install --upgrade git+git://github.com/geopython/pycsw.git@master#egg=pycsw
