from celery.decorators import task

from models import Service


@task(name="check_all_services")
def check_all_services_task():
    for service in Service.objects.filter(active=True).order_by('-last_updated'):
        service.update_layers()
        service.check()
        for layer in service.layer_set.all():
            layer.check()


@task(name="check_one_service")
def check_one_service_task(service_pk):
    service = Service.objects.get(pk=service_pk)
    service.update_layers()
    service.check()
    for layer in service.layer_set.all():
        layer.check()
