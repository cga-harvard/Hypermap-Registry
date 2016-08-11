import requests
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ("Set layer index scheme in Solr")

    args = 'path [path...]'

    def handle(self, *args, **options):

        """
        reset core:
        rm -Rf SOLR_HOME/server/solr/hypermap_test
        solr6 create_core -c hypermap_test
        """

        # read more here: https://cwiki.apache.org/confluence/display/solr/Schema+API
        schema_url = '%s/schema' % settings.SEARCH_URL
        schema_url = "http://localhost:8983/solr/hypermap_test/schema"

        # defining fields: https://cwiki.apache.org/confluence/display/solr/Defining+Fields
        # stored and indexed are default true.
        fields = [
            {"name": "abstract", "type": "string"},
            {"name": "area", "type": "tdouble"},
            {"name": "availability", "type": "string"},
            {"name": "bbox", "type": "location_rpt"},
            {"name": "domain_name", "type": "string"},
            {"name": "id", "type": "tlong", "required": True},
            {"name": "is_public", "type": "boolean"},
            {"name": "last_status", "type": "boolean"},
            {"name": "layer_date", "type": "tdate", "docValues": True},
            {"name": "layer_datetype", "type": "string"},
            {"name": "layer_id", "type": "tlong"},
            {"name": "layer_originator", "type": "string"},
            {"name": "location", "type": "string"},
            {"name": "max_x", "type": "tdouble"},
            {"name": "max_y", "type": "tdouble"},
            {"name": "min_x", "type": "tdouble"},
            {"name": "min_y", "type": "tdouble"},
            {"name": "name", "type": "string"},
            {"name": "recent_reliability", "type": "tdouble"},
            {"name": "reliability", "type": "tdouble"},
            {"name": "service_id", "type": "tlong"},
            {"name": "service_type", "type": "string"},
            {"name": "srs", "type": "string", "multiValued": True},
            {"name": "tile_url", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "type", "type": "string"},
            {"name": "url", "type": "string"},
        ]

        headers = {
            "Content-type": "application/json"
        }

        for field in fields:
            data = {
                "add-field": field
            }
            print data
            res = requests.post(schema_url, json=data, headers=headers)
            print res.text
            print '*' * 20
