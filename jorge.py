import requests, json

query = {'sort': {'_score': {'order': 'desc'}}, 'query': {'bool': {'filter': {
    'geo_shape': {'layer_geoshape': {'shape': {'type': 'envelope',
                                               'coordinates': [
                                                   ['-180.0', '90.0'],
                                                   ['180.0', '-90.0']]},
                                     'relation': 'intersects'}}}, 'must': [{
                                                                               'range': {
                                                                                   'layer_date': {
                                                                                       'gte': '1900-01-01T00:00:00Z',
                                                                                       'lte': '2016-12-31T00:00:00Z'}}}]}},
         'from': 0, 'aggs': {'articles_over_time': {
        'date_histogram': {'field': 'layer_date', 'interval': '1d',
                           'format': "yyyy-MM-dd'T'HH:mm:ssZ"}}}}

res = requests.post("http://localhost:9200/hypermap/_search", data=json.dumps(query))

print res.json()
