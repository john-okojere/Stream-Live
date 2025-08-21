# stream/admin.py
from django.contrib import admin
from .models import Sermon, Playlist, PlaylistItem, Library, PlayEvent

@admin.register(Sermon)
class SermonAdmin(admin.ModelAdmin):
    list_display = ("title", "speaker", "date", "duration_readable")
    search_fields = ("title", "speaker", "tags", "description")
    list_filter = ("speaker", "date")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("duration_s",)

    def duration_readable(self, obj):
        return obj.duration_hm()
    duration_readable.short_description = "Duration"

class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 0

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "is_public", "created_at")
    search_fields = ("title",)
    inlines = [PlaylistItemInline]

@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ("user", "sermon", "saved_at")
    search_fields = ("user__email", "sermon__title")

@admin.register(PlayEvent)
class PlayEventAdmin(admin.ModelAdmin):
    list_display = ("sermon", "user", "progress_s", "started_at", "completed_at")
    list_filter = ("sermon",)
