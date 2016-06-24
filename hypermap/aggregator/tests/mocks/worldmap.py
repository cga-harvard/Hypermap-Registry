# -*- coding: utf-8 -*-

"""
Mocks for testing a WorldMap service type.
"""

from httmock import response, urlmatch
import os


NETLOC = r'(.*\.)?worldmap\.harvard\.edu$'
HEADERS = {'content-type': 'application/json'}
GET = 'get'
API_PATH = os.path.abspath(os.path.dirname(__file__))


class Resource:
    """ A WorldMap resource.
    :param path: The file path to the resource.
    """

    def __init__(self, path):
        self.path = path

    def get(self):
        """ Perform a GET request on the resource.
        :rtype: str
        """
        with open(self.path) as f:
            content = f.read()
        return content


@urlmatch(netloc=NETLOC, method=GET)
def resource_get(url, request):
    file_path = '%s/%s%s' % (API_PATH, url.netloc, url.path)
    try:
        content = Resource(file_path).get()
    except EnvironmentError:
        # catch any environment errors (i.e. file does not exist) and return a
        # 404.
        return response(404, {}, HEADERS, None, 5, request)
    return response(200, content, HEADERS, None, 5, request)
