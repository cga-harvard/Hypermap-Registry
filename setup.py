import os
from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES

import hypermap


def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as ff:
        return ff.read()


def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join) in a
    platform-neutral way.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)

for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

packages, data_files = [], []
root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)
hypermap_dir = 'hypermap'

for dirpath, dirnames, filenames in os.walk(hypermap_dir):
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'):
            del dirnames[i]
    if '__init__.py' in filenames:
        packages.append('.'.join(fullsplit(dirpath)))
    elif filenames:
        data_files.append([dirpath, [os.path.join(dirpath, f) for f in filenames]])

setup(
    name="HHypermap",
    version=hypermap.__version__,
    author="",
    author_email="",
    description=hypermap.__description__,
    long_description=(read('README.md')),
    classifiers=[
        'Development Status :: 1 - Planning',
    ],
    license="BSD",
    keywords="hypermap django",
    url='https://github.com/cga-harvard/HHypermap',
    packages=packages,
    data_files=data_files,
    zip_safe=False,
    install_requires=[
        'amqplib==1.0.2',
        'arcrest==10.3',
        'celery==3.1.19',
        'Django==1.8.7',
        'django-debug-toolbar==1.4',
        'django-pagination==1.0.7',
        'django-taggit==0.18.0',
        'django-wsgi==1.0b1',
        'django-extensions==1.6.7',
        'dj-database-url==0.4.0',
        'pika==0.10.0',
        'pycsw==2.0.0',
        'flake8==2.5.1',
        'httmock==1.2.5',
        'MapProxy>=1.9.0',
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
    ]
)
