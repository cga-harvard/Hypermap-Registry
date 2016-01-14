from celery.decorators import task

from models import Service


@task(name="check_all_services")
def check_all_services_task():
    for service in Service.objects.filter(active=True):
        service.update_layers()
        service.check()
        for layer in service.layer_set.all():
            layer.check()
