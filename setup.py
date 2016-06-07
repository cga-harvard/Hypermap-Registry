import os
from distutils.core import setup

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name="HHyperMap",
    version="0.1",
    author="",
    author_email="",
    description="HHyperMap",
    long_description=(read('README.md')),
    # Full list of classifiers can be found at:
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
    ],
    license="BSD",
    keywords="hypermap django",
    url='https://github.com/cga-harvard/HHyperMap',
    packages=['hypermap',],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'amqplib==1.0.2',
        'arcrest==10.3',
        'celery==3.1.19',
        'Django==1.6.11',
        'django-debug-toolbar==1.2',
        'django-pagination==1.0.7',
        'django-polymorphic==0.8.1',
        'django-taggit==0.18.0',
        'django-wsgi==1.0b1',
        'flake8==2.5.1',
        'httmock==1.2.5',
        'MapProxy==1.8.1',
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
    ]
)
