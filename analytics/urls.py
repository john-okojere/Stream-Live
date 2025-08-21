from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/timeseries/", views.api_timeseries, name="api_timeseries"),
    path("api/top-pages/", views.api_top_pages, name="api_top_pages"),
    path("api/top-referrers/", views.api_top_referrers, name="api_top_referrers"),
    path("api/devices/", views.api_devices, name="api_devices"),
    path("api/os/", views.api_os, name="api_os"),
    path("api/browsers/", views.api_browsers, name="api_browsers"),
    path("api/geo/countries/", views.api_geo_countries, name="api_geo_countries"),
    path("api/geo/cities/", views.api_geo_cities, name="api_geo_cities"),
    
    path("api/top-sermons/", views.api_top_sermons, name="api_top_sermons"),
    path("event/", views.event_collect, name="event_collect"),
]
