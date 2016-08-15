import os
from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES

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
    name='django-registry',
    version='0.2.14',
    author='',
    author_email='',
    url='https://github.com/cga-harvard/HHypermap',
    download_url='https://github.com/cga-harvard/HHypermap',
    description='Django Registry by Harvard CGA',
    long_description=(read('README.md')),
    classifiers=[
        'Development Status :: 1 - Planning',
    ],
    license="BSD",
    keywords="hypermap django",
    packages=packages,
    data_files=data_files,
    zip_safe=False,
    install_requires=[
        'amqplib',
        'arcrest',
        'celery',
        'Django>=1.8, <1.9a0',
        'django-debug-toolbar',
        'django-pagination',
        'django-taggit',
        'django-extensions',
        'dj-database-url',
        'django-basic-authentication-decorator',
        'elasticsearch',
        'pika',
        'pycsw-hypermap',
        'flake8',
        'httmock',
        'djmp>=0.2.5',
        'MapProxy>=1.9',
        'djangorestframework',
        'django-celery',
        'isodate',
        'nose',
        'OWSLib',
        'Paver',
        'Pillow',
        'python-memcached',
        'psycopg2',
        'pysolr',
        'requests',
        'webtest',
    ]
)
