FROM python:2.7.9
MAINTAINER Ariel Núñez<ariel@terranodo.io>

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# This section is borrowed from the official Django image but adds GDAL and others
RUN apt-get update && apt-get install -y \
                gcc \
                gettext \
                postgresql-client libpq-dev \
                sqlite3 \
                python-gdal python-psycopg2 \
                python-imaging python-lxml \
                python-dev libgdal-dev \
                python-ldap \
                libmemcached-dev libsasl2-dev zlib1g-dev \
                vim \
        --no-install-recommends && rm -rf /var/lib/apt/lists/*


COPY wait-for-postgres.sh /usr/bin/wait-for-postgres
RUN chmod +x /usr/bin/wait-for-postgres

# To understand the next section (the need for requirements.txt and setup.py)
# Please read: https://packaging.python.org/requirements/

# python-gdal does not seem to work, let's install manually the version that is
# compatible with the provided libgdal-dev
RUN pip install GDAL==1.10 --global-option=build_ext --global-option="-I/usr/include/gdal"

# Copy the requirements first to avoid having to re-do it when the code changes.
# Requirements in requirements.txt are pinned to specific version
# usually the output of a pip freeze
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

# Update the requirements from the local env in case they differ from the pre-built ones.
ONBUILD COPY requirements.txt /usr/src/app/
ONBUILD RUN pip install --no-cache-dir -r requirements.txt

# Force a pycsw rebuild. Remove when pycsw 2.0.1 is released.
RUN pip uninstall -y pycsw
RUN rm -rf /usr/local/lib/python2.7/site-packages/pycsw/
RUN pip install --upgrade git+git://github.com/geopython/pycsw.git@2.0#egg=pycsw

ONBUILD COPY . /usr/src/app/
ONBUILD RUN pip install --no-deps --no-cache-dir -e /usr/src/app/

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
