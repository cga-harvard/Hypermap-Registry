from django.core.management.base import BaseCommand
from hypermap.aggregator.solr import SolrHypermap


class Command(BaseCommand):
    help = ("Set layer index scheme in Solr")

    args = 'path [path...]'

    def handle(self, *args, **options):
        """
        reset core:
        rm -Rf SOLR_HOME/server/solr/hypermap_test
        solr6 create_core -c hypermap_test
        """

        client = SolrHypermap()
        client.update_schema()
