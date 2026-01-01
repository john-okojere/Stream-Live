from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Event, Visit


class VisitResource(resources.ModelResource):
    class Meta:
        model = Visit
        fields = (
            "id",
            "ts",
            "path",
            "method",
            "status_code",
            "visitor_id",
            "user",
            "referer",
            "ua",
            "country",
            "city",
            "is_bot",
        )
        export_order = fields


@admin.register(Visit)
class VisitAdmin(ImportExportModelAdmin):
    resource_class = VisitResource
    list_display = ("ts", "path", "status_code", "visitor_id", "user", "is_bot")
    list_filter = ("is_bot", "status_code")
    search_fields = ("path", "visitor_id", "referer", "ua")
    date_hierarchy = "ts"


class EventResource(resources.ModelResource):
    class Meta:
        model = Event
        fields = (
            "id",
            "ts",
            "event",
            "slug",
            "title",
            "visitor_id",
            "user",
            "country",
            "city",
            "path",
        )
        export_order = fields


@admin.register(Event)
class EventAdmin(ImportExportModelAdmin):
    resource_class = EventResource
    list_display = ("ts", "event", "slug", "title", "visitor_id", "user", "country")
    list_filter = ("event", "country")
    search_fields = ("slug", "title", "path", "ua", "ip_hash")
    date_hierarchy = "ts"
