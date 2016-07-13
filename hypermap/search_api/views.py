import requests
from rest_framework.views import APIView
from rest_framework.response import Response

from .utils import parse_geo_box, request_time_facet, request_heatmap_facet
from .serializers import SearchSerializer

# - OPEN API specs
# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/1.2.md#parameterObject

TIME_FILTER_FIELD = "layer_date"
GEO_FILTER_FIELD = "bbox"
GEO_HEATMAP_FIELD = "bbox"
USER_FIELD = "layer_originator"
TEXT_FIELD = "title"
TIME_SORT_FIELD = "layer_date"
GEO_SORT_FIELD = "bbox"


def elasticsearch(serializer):
    """
    https://www.elastic.co/guide/en/elasticsearch/reference/current/_the_search_api.html
    :param serializer:
    :return:
    """
    search_engine_endpoint = serializer.validated_data.get("search_engine_endpoint")
    q_text = serializer.validated_data.get("q_text")
    return_search_engine_original_response = serializer.validated_data.get("return_search_engine_original_response")

    params = {
        "q": q_text
    }
    res = requests.get(search_engine_endpoint, params=params)
    es_response = res.json()

    if return_search_engine_original_response:
        return es_response

    data = {}

    hits = es_response.get("hits")
    data["a.matchDocs"] = hits.get("total")
    data["d.docs"] = hits.get("hits")

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
    d_docs_sort = serializer.validated_data.get("d_docs_sort")
    a_time_limit = serializer.validated_data.get("a_time_limit")
    a_time_gap = serializer.validated_data.get("a_time_gap")
    a_time_filter = serializer.validated_data.get("a_time_filter")
    a_hm_limit = serializer.validated_data.get("a_hm_limit")
    a_hm_gridlevel = serializer.validated_data.get("a_hm_gridlevel")
    a_hm_filter = serializer.validated_data.get("a_hm_filter")
    a_text_limit = serializer.validated_data.get("a_text_limit")
    a_user_limit = serializer.validated_data.get("a_user_limit")
    return_search_engine_original_response = serializer.validated_data.get("return_search_engine_original_response")

    print serializer.validated_data

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
    if filters: params["fq"] = filters

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

    if return_search_engine_original_response > 0:
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
        a_time = {
            "start": date_facet.get("start"),
            "end": date_facet.get("end"),
            "gap": date_facet.get("gap"),
            "counts": date_facet.get("counts")
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
        data["a.user"] = user_facet

    if a_text_limit > 0:
        text_facet = solr_response["facet_counts"]["facet_fields"][TEXT_FIELD]
        data["a.text"] = text_facet

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

    return data


class Search(APIView):
    """
    Swagger docs located in hypermap/api/static/swagger.yaml
    edit in http://editor.swagger.io/#/
    """

    def get(self, request):

        serializer = SearchSerializer(data=request.GET)
        if serializer.is_valid(raise_exception=True):

            search_engine = serializer.validated_data.get("search_engine")

            if search_engine == 'solr':
                data = solr(serializer)
            else:
                data = elasticsearch(serializer)

            status = 200
            if type(data) is tuple:
                status = data[0]
                data = data[1]

            return Response(data,
                            headers={'Access-Control-Allow-Origin': '*'},
                            status=status)