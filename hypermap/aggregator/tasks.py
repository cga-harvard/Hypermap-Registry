from celery.schedules import crontab
from celery.decorators import task

from healthcheck import check_service
from models import Service

@task(name="test_a_service")
def test_service_task():
    for service in Service.objects.all():
        check_service(service)
