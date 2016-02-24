from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ("Create MapProxy configuration for services")

    def handle(self, *args, **options):
        print "Creating config for services"
