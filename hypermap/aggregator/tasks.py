from celery.decorators import task


@task(name="check_all_services")
def check_all_services():
    from models import Service
    for service in Service.objects.filter(active=True).order_by('-last_updated'):
        service.update_layers()
        service.check()
        for layer in service.layer_set.all():
            layer.check()


@task(name="check_specific_service")
def check_service(service):
    service.update_layers()
    service.check()
    for layer in service.layer_set.all():
        layer.check()


@task(name="check_specific_layer")
def check_layer(layer):
    layer.check()


@task(name="update_endpoints")
def update_endpoints(endpoint_list):
    from aggregator.utils import create_services_from_endpoint, get_sanitized_endpoint
    for endpoint in endpoint_list.endpoint_set.all():
        if not endpoint.processed:
            print endpoint.url
            sanitized_url = get_sanitized_endpoint(endpoint.url)
            imported, message = create_services_from_endpoint(sanitized_url)
            endpoint.imported = imported
            endpoint.message = message
            endpoint.processed = True
            endpoint.save()
        else:
            print 'This enpoint was already processed'
    return True
