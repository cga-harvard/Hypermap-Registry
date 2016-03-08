from django.contrib import admin

# Register your models here.
from models import Dynasty


class DynastyAdmin(admin.ModelAdmin):
    model = Dynasty
    list_display = ('date_range', 'name')

admin.site.register(Dynasty, DynastyAdmin)
