# -*- coding: utf-8 -*-
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from hypermap.aggregator.models import Catalog
from django.conf import settings
from .utils import parse_geo_box, request_time_facet, \
                request_heatmap_facet, gap_to_elastic, \
                asterisk_to_min_max
from .serializers import SearchSerializer, CatalogSerializer
import json

# - OPEN API specs
# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/1.2.md#parameterObject

TIME_FILTER_FIELD = "layer_date"
GEO_FILTER_FIELD = "bbox"
GEO_HEATMAP_FIELD = "bbox"
USER_FIELD = "layer_originator"
TEXT_FIELD = "title"
TIME_SORT_FIELD = "layer_date"
GEO_SORT_FIELD = "bbox"

REGISTRY_SEARCH_URL = getattr(settings, "REGISTRY_SEARCH_URL", "elasticsearch+http://localhost:9200")

SEARCH_TYPE = REGISTRY_SEARCH_URL.split('+')[0]
SEARCH_URL = REGISTRY_SEARCH_URL.split('+')[1]


def elasticsearch(serializer, catalog):
    """
    https://www.elastic.co/guide/en/elasticsearch/reference/current/_the_search_api.html
    :param serializer:
    :return:
    """

    search_engine_endpoint = "{0}/{1}/_search".format(SEARCH_URL, catalog.slug)

    q_text = serializer.validated_data.get("q_text")
    q_time = serializer.validated_data.get("q_time")
    q_geo = serializer.validated_data.get("q_geo")
    q_user = serializer.validated_data.get("q_user")
    d_docs_sort = serializer.validated_data.get("d_docs_sort")
    d_docs_limit = int(serializer.validated_data.get("d_docs_limit"))
    d_docs_page = int(serializer.validated_data.get("d_docs_page"))
    a_text_limit = serializer.validated_data.get("a_text_limit")
    a_user_limit = serializer.validated_data.get("a_user_limit")
    a_time_gap = serializer.validated_data.get("a_time_gap")
    a_time_limit = serializer.validated_data.get("a_time_limit")
    original_response = serializer.validated_data.get("original_response")

    # Dict for search on Elastic engine
    must_array = []
    filter_dic = {}
    aggs_dic = {}

    # String searching
    if q_text:
        # Wrapping query string into a query filter.
        query_string = {
            "query": {
                "query_string": {
                    "query": q_text
                }
            }
        }
        # add string searching
        must_array.append(query_string)

    if q_time:
        # check if q_time exists
        q_time = str(q_time)  # check string
        shortener = q_time[1:-1]
        shortener = shortener.split(" TO ")
        gte = shortener[0]  # greater than
        lte = shortener[1]  # less than
        layer_date = {}
        if gte == '*' and lte != '*':
            layer_date["lte"] = lte
            range_time = {
                "layer_date": layer_date
            }
            range_time = {"range": range_time}
            must_array.append(range_time)
        if gte != '*' and lte == '*':
            layer_date["gte"] = gte
            range_time = {
                "layer_date": layer_date
            }
            range_time = {"range": range_time}
            must_array.append(range_time)
        if gte != '*' and lte != '*':
            layer_date["gte"] = gte
            layer_date["lte"] = lte
            range_time = {
                "layer_date": layer_date
            }
            range_time = {"range": range_time}
            must_array.append(range_time)
    # geo_shape searching
    if q_geo:
        q_geo = str(q_geo)
        q_geo = q_geo[1:-1]
        Ymin, Xmin = q_geo.split(" TO ")[0].split(",")
        Ymax, Xmax = q_geo.split(" TO ")[1].split(",")
        geoshape_query = {
            "layer_geoshape": {
                "shape": {
                    "type": "envelope",
                    "coordinates": [[Xmin, Ymax], [Xmax, Ymin]]
                },
                "relation": "intersects"
            }
        }
        filter_dic["geo_shape"] = geoshape_query

    if q_user:
        # Using q_user
        user_searching = {
            "match": {
                "layer_originator": q_user
            }
        }
        must_array.append(user_searching)

    dic_query = {
        "query": {
            "filtered": {
                "filter":{
                    "bool": {
                        "must": must_array,
                        "should": filter_dic
                    }
                }
            }
        }
    }

    # Page
    if d_docs_limit:
        dic_query["size"] = d_docs_limit

    if d_docs_page:
        dic_query["from"] = d_docs_limit * d_docs_page - d_docs_limit

    if d_docs_sort == "score":
        dic_query["sort"] = {"_score": {"order": "desc"}}

    if d_docs_sort == "time":
        dic_query["sort"] = {"layer_date": {"order": "desc"}}

    if d_docs_sort == "distance":
        if q_geo:
            # distance_x = float(((float(Xmin) - float(Xmax)) ** 2.0) ** (0.5))
            # distance_y = float(((float(Ymin) - float(Ymax)) ** 2.0) ** (0.5))
            msg = ("Sorting by distance is different on ElasticSearch than Solr, because this"
                   "feature on elastic is unavailable to geo_shape type.ElasticSearch docs said:"
                   "Due to the complex input structure and index representation of shapes,"
                   "it is not currently possible to sort shapes or retrieve their fields directly."
                   "The geo_shape value is only retrievable through the _source field."
                   " Link: https://www.elastic.co/guide/en/elasticsearch/reference/current/geo-shape.html")
            return {"error": {"msg": msg}}

        else:
            msg = "q_qeo MUST BE NO ZERO if you wanna sort by distance"
            return {"error": {"msg": msg}}

    if a_text_limit:
        # getting most frequently occurring users.
        text_limit = {
            "terms": {
                "field": "abstract",
                "size": a_text_limit
            }
        }
        aggs_dic['popular_text'] = text_limit

    if a_user_limit:
        # getting most frequently occurring users.
        users_limit = {

            "terms": {
                "field": "layer_originator",
                "size": a_user_limit
            }
        }
        aggs_dic['popular_users'] = users_limit

    if a_time_limit:
        # TODO: Work in progress, a_time_limit is incomplete.
        # TODO: when times are * it does not work. also a a_time_gap is not required.
        if q_time:
            if not a_time_gap:
                # getting time limit histogram.
                time_limt = {
                    "date_range": {
                        "field": "layer_date",
                        "format": "yyyy-MM-dd'T'HH:mm:ssZ",
                        "ranges": [
                            {"from": gte, "to": lte}
                        ]
                    }
                }
                aggs_dic['range'] = time_limt
            else:
                pass

        else:
            msg = "If you want to use a_time_limit feature, q_time MUST BE initialized"
            return {"error": {"msg": msg}}

    if a_time_gap:
        interval = gap_to_elastic(a_time_gap)
        time_gap = {
            "date_histogram": {
                "field": "layer_date",
                "format": "yyyy-MM-dd'T'HH:mm:ssZ",
                "interval": interval
            }
        }
        aggs_dic['articles_over_time'] = time_gap

    # adding aggreations on body query
    if aggs_dic:
        dic_query['aggs'] = aggs_dic
    try:
        res = requests.post(search_engine_endpoint, data=json.dumps(dic_query))
    except Exception as e:
        return 500, {"error": {"msg": str(e)}}

    es_response = res.json()

    if original_response:
        return es_response

    data = {}

    if 'error' in es_response:
        data["error"] = es_response["error"]
        return 400, data

    data["request_url"] = res.url
    data["request_body"] = json.dumps(dic_query)
    data["a.matchDocs"] = es_response['hits']['total']
    docs = []
    # aggreations response: facets searching
    if 'aggregations' in es_response:
        aggs = es_response['aggregations']
        # getting the most frequently occurring users.
        if 'popular_users' in aggs:
            a_users_list_array = []
            users_resp = aggs["popular_users"]["buckets"]
            for item in users_resp:
                temp = {}
                temp['count'] = item['doc_count']
                temp['value'] = item['key']
                a_users_list_array.append(temp)
            data["a.user"] = a_users_list_array

        # getting most frequently ocurring words
        if 'popular_text' in aggs:
            a_text_list_array = []
            text_resp = es_response["aggregations"]["popular_text"]["buckets"]
            for item in text_resp:
                temp = {}
                temp['count'] = item['doc_count']
                temp['value'] = item['key']
                a_text_list_array.append(temp)
            data["a.text"] = a_text_list_array

        if 'articles_over_time' in aggs:
            gap_count = []
            a_gap = {}
            gap_resp = aggs["articles_over_time"]["buckets"]

            start = "*"
            end = "*"

            if len(gap_resp) > 0:
                start = gap_resp[0]['key_as_string'].replace('+0000', 'z')
                end = gap_resp[-1]['key_as_string'].replace('+0000', 'z')

            a_gap['start'] = start
            a_gap['end'] = end
            a_gap['gap'] = a_time_gap

            for item in gap_resp:
                temp = {}
                if item['doc_count'] != 0:
                    temp['count'] = item['doc_count']
                    temp['value'] = item['key_as_string'].replace('+0000', 'z')
                    gap_count.append(temp)
            a_gap['counts'] = gap_count
            data['a.time'] = a_gap

        if 'range' in aggs:
            # Work in progress
            # Pay attention in the following code lines: Make it better!!!!
            time_count = []
            time_resp = aggs["range"]["buckets"]
            a_time = {}
            a_time['start'] = gte
            a_time['end'] = lte
            a_time['gap'] = None

            for item in time_resp:
                temp = {}
                if item['doc_count'] != 0:
                    temp['count'] = item['doc_count']
                    temp['value'] = item['key'].replace('+0000', 'z')
                    time_count.append(temp)
            a_time['counts'] = time_count
            data['a.time'] = a_time

    if not int(d_docs_limit) == 0:
        for item in es_response['hits']['hits']:
            # data
            temp = item['_source']['abstract']
            temp = temp.replace(u'\u201c', "\"")
            temp = temp.replace(u'\u201d', "\"")
            temp = temp.replace('"', "\"")
            temp = temp.replace("'", "\'")
            temp = temp.replace(u'\u2019', "\'")
            item['_source']['abstract'] = temp
            docs.append(item['_source'])

    data["d.docs"] = docs

    return data


def solr(serializer):
    """
    Search on solr endpoint
    :param serializer:
    :return:
    """
    search_engine_endpoint = serializer.validated_data.get("search_engine_endpoint")
    q_time = serializer.validated_data.get("q_time")
    q_geo = serializer.validated_data.get("q_geo")
    q_text = serializer.validated_data.get("q_text")
    q_user = serializer.validated_data.get("q_user")
    d_docs_limit = serializer.validated_data.get("d_docs_limit")
    d_docs_page = serializer.validated_data.get("d_docs_page")
    d_docs_sort = serializer.validated_data.get("d_docs_sort")
    a_time_limit = serializer.validated_data.get("a_time_limit")
    a_time_gap = serializer.validated_data.get("a_time_gap")
    a_time_filter = serializer.validated_data.get("a_time_filter")
    a_hm_limit = serializer.validated_data.get("a_hm_limit")
    a_hm_gridlevel = serializer.validated_data.get("a_hm_gridlevel")
    a_hm_filter = serializer.validated_data.get("a_hm_filter")
    a_text_limit = serializer.validated_data.get("a_text_limit")
    a_user_limit = serializer.validated_data.get("a_user_limit")
    original_response = serializer.validated_data.get("original_response")

    # query params to be sent via restful solr
    params = {
        "q": "*:*",
        "indent": "on",
        "wt": "json",
        "rows": d_docs_limit,
        "facet": "off",
        "facet.field": [],
        "debug": "timing"
    }
    if q_text:
        params["q"] = q_text

    if d_docs_limit >= 0:
        d_docs_page -= 1
        d_docs_page = d_docs_limit * d_docs_page
        params["start"] = d_docs_page

    # query params for filters
    filters = []
    if q_time:
        # TODO: when user sends incomplete dates like 2000, its completed: 2000-(TODAY-MONTH)-(TODAY-DAY)T00:00:00Z
        # TODO: "Invalid Date in Date Math String:'[* TO 2000-12-05T00:00:00Z]'"
        # Kotlin like: "{!field f=layer_date tag=layer_date}[* TO 2000-12-05T00:00:00Z]"
        # then do it simple:
        filters.append("{0}:{1}".format(TIME_FILTER_FIELD, q_time))
    if q_geo:
        filters.append("{0}:{1}".format(GEO_FILTER_FIELD, q_geo))

    if q_user:
        filters.append("{{!field f={0} tag={0}}}{1}".format(USER_FIELD, q_user))

    if filters:
        params["fq"] = filters

    # query params for ordering
    if d_docs_sort == 'score' and q_text:
        params["sort"] = 'score desc'
    elif d_docs_sort == 'time':
        params["sort"] = '{} desc'.format(TIME_SORT_FIELD)
    elif d_docs_sort == 'distance':
        rectangle = parse_geo_box(q_geo)
        params["sort"] = 'geodist() asc'
        params["sfield"] = GEO_SORT_FIELD
        params["pt"] = '{0},{1}'.format(rectangle.centroid.x, rectangle.centroid.y)

    # query params for facets
    if a_time_limit > 0:
        params["facet"] = 'on'
        time_filter = a_time_filter or q_time or None

        # traduce * to actual min/max dates.
        time_filter = asterisk_to_min_max(TIME_FILTER_FIELD, time_filter, search_engine_endpoint)

        # create the range faceting params.
        facet_parms = request_time_facet(TIME_FILTER_FIELD, time_filter, a_time_gap, a_time_limit)
        params.update(facet_parms)

    if a_hm_limit > 0:
        params["facet"] = 'on'
        hm_facet_params = request_heatmap_facet(GEO_HEATMAP_FIELD, a_hm_filter, a_hm_gridlevel, a_hm_limit)
        params.update(hm_facet_params)

    if a_text_limit > 0:
        params["facet"] = 'on'
        params["facet.field"].append(TEXT_FIELD)
        params["f.{}.facet.limit".format(TEXT_FIELD)] = a_text_limit

    if a_user_limit > 0:
        params["facet"] = 'on'
        params["facet.field"].append("{{! ex={0}}}{0}".format(USER_FIELD))
        params["f.{}.facet.limit".format(USER_FIELD)] = a_user_limit

    try:
        res = requests.get(
            search_engine_endpoint, params=params
        )
    except Exception as e:
        return 500, {"error": {"msg": str(e)}}

    print '>', res.url

    solr_response = res.json()
    solr_response["solr_request"] = res.url

    if original_response > 0:
        return solr_response

    # create the response dict following the swagger model:
    data = {}

    if 'error' in solr_response:
        data["error"] = solr_response["error"]
        return 400, data

    response = solr_response["response"]
    data["a.matchDocs"] = response.get("numFound")

    if response.get("docs"):
        data["d.docs"] = response.get("docs")

    if a_time_limit > 0:
        date_facet = solr_response["facet_counts"]["facet_ranges"][TIME_FILTER_FIELD]
        counts = []
        value_count = iter(date_facet.get("counts"))
        for value, count in zip(value_count, value_count):
            counts.append({
                "value": value,
                "count": count
            })
        a_time = {
            "start": date_facet.get("start"),
            "end": date_facet.get("end"),
            "gap": date_facet.get("gap"),
            "counts": counts
        }
        data["a.time"] = a_time

    if a_hm_limit > 0:
        hm_facet_raw = solr_response["facet_counts"]["facet_heatmaps"][GEO_HEATMAP_FIELD]
        hm_facet = {
            'gridLevel': hm_facet_raw[1],
            'columns': hm_facet_raw[3],
            'rows': hm_facet_raw[5],
            'minX': hm_facet_raw[7],
            'maxX': hm_facet_raw[9],
            'minY': hm_facet_raw[11],
            'maxY': hm_facet_raw[13],
            'counts_ints2D': hm_facet_raw[15],
            'projection': 'EPSG:4326'
        }
        data["a.hm"] = hm_facet

    if a_user_limit > 0:
        user_facet = solr_response["facet_counts"]["facet_fields"][USER_FIELD]

        counts = []
        value_count = iter(user_facet)
        for value, count in zip(value_count, value_count):
            counts.append({
                "value": value,
                "count": count
            })
        data["a.user"] = counts

    if a_text_limit > 0:
        text_facet = solr_response["facet_counts"]["facet_fields"][TEXT_FIELD]

        counts = []
        value_count = iter(text_facet)
        for value, count in zip(value_count, value_count):
            counts.append({
                "value": value,
                "count": count
            })
        data["a.text"] = counts

    subs = []
    for label, values in solr_response["debug"]["timing"].iteritems():
        if type(values) is not dict:
            continue
        subs_data = {"label": label, "subs": []}
        for label, values in values.iteritems():
            if type(values) is not dict:
                subs_data["millis"] = values
                continue
            subs_data["subs"].append({
                "label": label,
                "millis": values.get("time")
            })
        subs.append(subs_data)

    timing = {
        "label": "requests.get.elapsed",
        "millis": res.elapsed,
        "subs": [{
            "label": "QTime",
            "millis": solr_response["responseHeader"].get("QTime"),
            "subs": subs
        }]
    }

    data["timing"] = timing
    data["request_url"] = res.url

    return data


def parse_get_params(request):
    """
    parse all url get params that contains dots in a representation of
    serializer field names, for example: d.docs.limit to d_docs_limit.
    that makes compatible an actual API client with django-rest-framework
    serializers.
    :param request:
    :return: QueryDict with parsed get params.
    """

    get = request.GET.copy()
    new_get = request.GET.copy()
    for key in get.iterkeys():
        if key.count(".") > 0:
            new_key = key.replace(".", "_")
            new_get[new_key] = get.get(key)
            del new_get[key]

    return new_get


class Search(APIView):
    """
    Swagger docs located in hypermap/api/static/swagger.yaml
    edit in http://editor.swagger.io/#/
    """

    def get(self, request, catalog_slug):

        request.GET = parse_get_params(request)
        serializer = SearchSerializer(data=request.GET)
        if serializer.is_valid(raise_exception=True):

            try:
                catalog = Catalog.objects.get(slug=catalog_slug)
            except Catalog.DoesNotExist:
                return Response({"error": "catalog '{}' not found".format(catalog_slug)},
                                status=404)

            # check if data source is remote
            # if catalog.is_remote and request.META['SERVER_PORT'] == "8000":
            if catalog.is_remote:
                response = requests.get(catalog.url, params=request.query_params)
                if response.status_code in [200, 400]:
                    return Response(response.json(),
                                    status=response.status_code)
                else:
                    return Response(response.text,
                                    status=response.status_code)

            search_engine = serializer.validated_data.get("search_engine", "elasticsearch")
            if search_engine == 'solr':
                data = solr(serializer)
            else:
                data = elasticsearch(serializer, catalog)

            status = 200
            if type(data) is tuple:
                status = data[0]
                data = data[1]

            return Response(data, status=status)


class CatalogViewSet(ModelViewSet):
    queryset = Catalog.objects.all()
    serializer_class = CatalogSerializer
