from django.contrib import admin

from models import Service, Layer, Check, SpatialReferenceSystem

class ServiceAdmin(admin.ModelAdmin):
    model = Service
    list_display = ('type', 'title', 'active', )
    list_display_links = ('title', )


class SpatialReferenceSystemAdmin(admin.ModelAdmin):
    model = SpatialReferenceSystem
    list_display = ('code', )


class LayerAdmin(admin.ModelAdmin):
    model = Layer
    list_display = ('name', 'title', 'service', )


class CheckAdmin(admin.ModelAdmin):
    model = Check
    list_display = ('resource', 'checked_datetime', 'success', 'response_time', )
    list_display_links = ('resource', )


admin.site.register(Service, ServiceAdmin)
admin.site.register(Check, CheckAdmin)
admin.site.register(SpatialReferenceSystem, SpatialReferenceSystemAdmin)
admin.site.register(Layer, LayerAdmin)

# we like to see celery results using the admin
from djcelery.models import TaskMeta

class TaskMetaAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'date_done', 'status', )

admin.site.register(TaskMeta, TaskMetaAdmin)
