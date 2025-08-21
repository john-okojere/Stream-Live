from django.urls import path
from . import views, api

app_name = "stream"

urlpatterns = [
    path("", views.SermonListView.as_view(), name="past_list"),
    path("<slug:slug>/", views.SermonDetailView.as_view(), name="past_detail"),
    path("upload/", views.upload_sermon, name="upload_sermon"),  # staff-only

    # JSON endpoints
    path("api/sermons/<slug:slug>.json", api.sermon_json, name="sermon_json"),
    path("api/search.json", api.search_json, name="search_json"),
    path("api/library/toggle/", api.library_toggle, name="library_toggle"),
    path("api/progress/", api.progress_ping, name="progress_ping"),
]

from .views import sermons_list_json
urlpatterns += [
    path("api/sermons/", sermons_list_json, name="sermons_list_json"),
    path("api/sidebar/summary/", views.sidebar_summary_json, name="sidebar_summary_json"),
]
