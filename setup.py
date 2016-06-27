import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

setup(
    name='django-registry',
    version='0.2',
    author='',
    author_email='',
    url='https://github.com/cga-harvard/HHypermap',
    download_url='https://github.com/cga-harvard/HHypermap',
    description='Django Registry by Harvard CGA',
    long_description=open(os.path.join(here, 'README.md')).read(),
    license='See LICENSE file.',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 1 - Planning',
    ],
    install_requires=[
        'amqplib==1.0.2',
        'arcrest==10.3',
        'celery==3.1.19',
        'Django==1.8.7',
        'django-debug-toolbar==1.4',
        'django-pagination==1.0.7',
        'django-polymorphic==0.8.1',
        'django-taggit==0.18.0',
        'django-wsgi==1.0b1',
        'django-extensions==1.6.7',
        'dj-database-url==0.4.0',
        'pika==0.10.0',
        'pycsw==2.0.0-alpha1',
        'flake8==2.5.1',
        'httmock==1.2.5',
        # For ArcGIS support we need to install the latest from Github.
        # once the new MapProxy is release we will update here and remove this notice.
        'MapProxy==1.8.1',
        'pyelasticsearch==1.4',
        'django-celery==3.1.17',
        'nose==1.3.7',
        'OWSLib==0.10.3',
        'Paver==1.2.4',
        'Pillow==3.1.0.rc1',
        'python-memcached==1.57',
        'psycopg2==2.6.1',
        'pysolr==3.3.3',
        'pyelasticsearch==1.4',
        'requests==2.9.1',
        'webtest==2.0.20',
        'django-maploom-registry',
    ]
)
