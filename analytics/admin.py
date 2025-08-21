from django.contrib import admin
from .models import Visit, Event

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("ts", "path", "status_code", "visitor_id", "user", "is_bot")
    list_filter = ("is_bot", "status_code")
    search_fields = ("path", "visitor_id", "referer", "ua")
    date_hierarchy = "ts"

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("ts", "event", "slug", "title", "visitor_id", "user", "country")
    list_filter = ("event", "country")
    search_fields = ("slug", "title", "path", "ua", "ip_hash")
    date_hierarchy = "ts"
