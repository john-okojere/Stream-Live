# stream/admin.py
from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Library, PlayEvent, Playlist, PlaylistItem, Sermon


class SermonResource(resources.ModelResource):
    class Meta:
        model = Sermon
        fields = (
            "id",
            "title",
            "slug",
            "speaker",
            "date",
            "cover",
            "audio",
            "uploaded_by",
            "tags",
            "description",
            "duration_s",
        )
        export_order = fields


@admin.register(Sermon)
class SermonAdmin(ImportExportModelAdmin):
    resource_class = SermonResource
    list_display = ("title", "speaker", "date", "uploaded_by", "duration_readable")
    search_fields = ("title", "speaker", "tags", "description", "uploaded_by__email")
    list_filter = ("speaker", "date", "uploaded_by")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("duration_s",)

    def duration_readable(self, obj):
        return obj.duration_hm()

    duration_readable.short_description = "Duration"


class PlaylistResource(resources.ModelResource):
    class Meta:
        model = Playlist
        fields = ("id", "title", "slug", "owner", "is_public", "created_at")
        export_order = fields


class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 0


@admin.register(Playlist)
class PlaylistAdmin(ImportExportModelAdmin):
    resource_class = PlaylistResource
    list_display = ("title", "owner", "is_public", "created_at")
    search_fields = ("title",)
    inlines = [PlaylistItemInline]


class LibraryResource(resources.ModelResource):
    class Meta:
        model = Library
        fields = ("id", "user", "sermon", "saved_at")
        export_order = fields


@admin.register(Library)
class LibraryAdmin(ImportExportModelAdmin):
    resource_class = LibraryResource
    list_display = ("user", "sermon", "saved_at")
    search_fields = ("user__email", "sermon__title")


class PlayEventResource(resources.ModelResource):
    class Meta:
        model = PlayEvent
        fields = ("id", "sermon", "user", "progress_s", "started_at", "completed_at")
        export_order = fields


@admin.register(PlayEvent)
class PlayEventAdmin(ImportExportModelAdmin):
    resource_class = PlayEventResource
    list_display = ("sermon", "user", "progress_s", "started_at", "completed_at")
    list_filter = ("sermon",)
