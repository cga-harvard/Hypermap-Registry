from django.contrib import admin

from django_celery_results.models import TaskResult

from models import (Service, Layer, Check, SpatialReferenceSystem, EndpointList,
                    Endpoint, LayerDate, LayerWM, Catalog, IssueType, Issue)


class ServiceAdmin(admin.ModelAdmin):
    model = Service
    list_display = ('id', 'type', 'is_valid', 'title', 'active', 'url', )
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
    list_display = ('name', 'is_valid',  'title', 'service', )
    search_fields = ['name', 'title', ]
    list_filter = ('is_public', )


class LayerWMAdmin(admin.ModelAdmin):
    model = LayerWM
    list_display = ('layer', 'username', 'category', 'temporal_extent_start', 'temporal_extent_end')


class CheckAdmin(admin.ModelAdmin):
    model = Check
    list_display = ('id', 'content_type', 'content_object', 'checked_datetime', 'success', 'response_time', )
    search_fields = ['=object_id']
    list_filter = ('success', 'content_type')
    date_hierarchy = 'checked_datetime'


class EndpointListAdmin(admin.ModelAdmin):
    model = EndpointList
    list_display = ('id', 'upload', 'endpoints_admin_url', 'catalog', 'greedy')


class EndpointAdmin(admin.ModelAdmin):
    model = Endpoint
    list_display = ('url', 'processed_datetime', 'processed', 'imported', 'message', 'endpoint_list')
    list_filter = ('processed', 'imported')
    search_fields = ['url', ]


class CatalogAdmin(admin.ModelAdmin):
    model = Catalog
    list_display = ('name', 'slug', 'url', 'get_search_url')
    search_fields = ('name', )


class IssueTypeAdmin(admin.ModelAdmin):
    model = IssueType
    list_display = ('description',)
    search_fields = ('description',)


class IssueAdmin(admin.ModelAdmin):
    model = Issue
    list_display = ('id', 'content_type', 'content_object_link', 'issue_type', 'description')
    list_display_links = ('id',)
    search_fields = ['=object_id', 'description', ]
    list_filter = ('content_type', 'issue_type',)

    def content_object_link(self, obj):
        return u'<a href="../%s/%s">%s</a>' % (obj.content_type, obj.content_object, obj.content_object)

    content_object_link.allow_tags = True
    content_object_link.short_description = 'content object'

admin.site.register(Service, ServiceAdmin)
admin.site.register(Check, CheckAdmin)
admin.site.register(SpatialReferenceSystem, SpatialReferenceSystemAdmin)
admin.site.register(Layer, LayerAdmin)
admin.site.register(LayerWM, LayerWMAdmin)
admin.site.register(LayerDate, LayerDateAdmin)
admin.site.register(EndpointList, EndpointListAdmin)
admin.site.register(Endpoint, EndpointAdmin)
admin.site.register(Catalog, CatalogAdmin)
admin.site.register(IssueType, IssueTypeAdmin)
admin.site.register(Issue, IssueAdmin)


class CustomTaskResultAdmin(admin.ModelAdmin):
    """
    HHypermap customized Admin-interface for results of tasks.
    """

    model = TaskResult
    list_display = (
        'task_id', 'date_done', 'task_name', 'status', 'task_arguments')
    readonly_fields = (
        'date_done', 'result', 'hidden', 'meta', 'task_arguments', 'task_name')
    fieldsets = (
        (None, {
            'fields': (
                'task_id',
                'task_name',
                'status',
                'content_type',
                'task_arguments',
                'content_encoding',
            ),
            'classes': ('extrapretty', 'wide')
        }),
        ('Result', {
            'fields': (
                'result',
                'date_done',
                'traceback',
                'hidden',
                'meta',
            ),
            'classes': ('extrapretty', 'wide')
        }),
    )
    list_filter = ('task_name', 'status', )
    date_hierarchy = 'date_done'

admin.site.unregister(TaskResult)
admin.site.register(TaskResult, CustomTaskResultAdmin)
