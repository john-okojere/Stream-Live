from django.contrib import admin
from .models import Sermon

@admin.register(Sermon)
class SermonAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "speaker", "duration_s")
    list_filter = ("date", "speaker")
    search_fields = ("title", "speaker", "description", "tags")
    prepopulated_fields = {"slug": ("title",)}
