import csv
from optparse import make_option

from django.core.management.base import BaseCommand

from hypermap.aggregator.utils import create_services_from_endpoint, get_sanitized_endpoint


class Command(BaseCommand):
    help = ("Check service/services and its/their layers based on a filter.")

    args = 'path [path...]'

    option_list = BaseCommand.option_list + (
        make_option(
            '-c',
            '--column',
            dest="column",
            default=0,
            help="Column index containing endpoints in csv"),
    )

    def handle(self, *args, **options):
        column = int(options.get('column'))
        csv_file = args[0]
        with open(csv_file, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                print row[column]
                endpoint = get_sanitized_endpoint(row[column])
                create_services_from_endpoint(endpoint)
