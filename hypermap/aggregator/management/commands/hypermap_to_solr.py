from django.core.management.base import NoArgsCommand
from aggregator import utils


class Command(NoArgsCommand):
    help = """
    """

    def handle_noargs(self, **options):
        utils.OGP_utils.geonode_to_solr()
