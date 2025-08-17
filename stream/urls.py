from django.urls import path
from . import views

app_name = "stream"

urlpatterns = [
    path("", views.live, name="live"),
    path("past/", views.past_list, name="past_list"),
    path("past/<slug:slug>/", views.past_detail, name="past_detail"),
    path("upload/", views.upload_sermon, name="upload_sermon"),  # staff-only
]
