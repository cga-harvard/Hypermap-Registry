from django.contrib import admin

from djcelery.models import TaskMeta

from models import (Service, Layer, Check, SpatialReferenceSystem, EndpointList,
                    Endpoint, LayerDate, LayerWM, TaskError)


class ServiceAdmin(admin.ModelAdmin):
    model = Service
    list_display = ('id', 'type', 'title', 'active', 'url', )
    list_display_links = ('id', )
    search_fields = ['title', 'url', ]
    list_filter = ('type', )


class SpatialReferenceSystemAdmin(admin.ModelAdmin):
    model = SpatialReferenceSystem
    list_display = ('code', )


class LayerDateAdmin(admin.ModelAdmin):
    model = LayerDate
    list_display = ('date', 'type', 'layer', 'layer_abstract')
    list_filter = ('type', )

    def layer_abstract(self, instance):
        return instance.layer.abstract


class LayerAdmin(admin.ModelAdmin):
    model = Layer
    list_display = ('name', 'title', 'service', )
    search_fields = ['name', 'title', ]
    list_filter = ('is_public', )


class LayerWMAdmin(admin.ModelAdmin):
    model = LayerWM
    list_display = ('layer', 'username', 'category', 'temporal_extent_start', 'temporal_extent_end')


class CheckAdmin(admin.ModelAdmin):
    model = Check
    list_display = ('id', 'content_type', 'content_object', 'checked_datetime', 'success', 'response_time', )
    search_fields = ['object_id']
    list_filter = ('success', 'content_type')
    date_hierarchy = 'checked_datetime'


class EndpointListAdmin(admin.ModelAdmin):
    model = EndpointList
    list_display = ('id', 'upload', 'endpoints_admin_url', )


class EndpointAdmin(admin.ModelAdmin):
    model = Endpoint
    list_display = ('url', 'processed_datetime', 'processed', 'imported', 'message', 'endpoint_list')
    list_filter = ('processed', 'imported')
    search_fields = ['url', ]


class TaskErrorAdmin(admin.ModelAdmin):
    model = TaskError
    list_display = ('task_name', 'args', 'error_datetime', 'message')
    list_filter = ('task_name',)
    date_hierarchy = 'error_datetime'


admin.site.register(Service, ServiceAdmin)
admin.site.register(Check, CheckAdmin)
admin.site.register(SpatialReferenceSystem, SpatialReferenceSystemAdmin)
admin.site.register(Layer, LayerAdmin)
admin.site.register(LayerWM, LayerWMAdmin)
admin.site.register(LayerDate, LayerDateAdmin)
admin.site.register(EndpointList, EndpointListAdmin)
admin.site.register(Endpoint, EndpointAdmin)
admin.site.register(TaskError, TaskErrorAdmin)


# we like to see celery results using the admin
class TaskMetaAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'date_done', 'status', )

admin.site.register(TaskMeta, TaskMetaAdmin)
