# accounts/urls.py
from django.urls import path

from . import views
from .views import (
    login_view, profile_view, register_view, logout_view, dashboard,
    MyPasswordResetView, MyPasswordResetDoneView,
    MyPasswordResetConfirmView, MyPasswordResetCompleteView,
    MyPasswordChangeView, MyPasswordChangeDoneView,
)

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("", dashboard, name="dashboard"),
    path("<uuid:uid>/", profile_view, name="profile"),

    path("password-reset/", MyPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", MyPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", MyPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/complete/", MyPasswordResetCompleteView.as_view(), name="password_reset_complete"),

    path("password-change/", MyPasswordChangeView.as_view(), name="password_change"),
    path("password-change/done/", MyPasswordChangeDoneView.as_view(), name="password_change_done"),
    
    path("dashboard/export/", views.dashboard_export_csv, name="dashboard_export"),

    # Users management (Admin-only UI)
    path("users/", views.users_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<uuid:uid>/edit/", views.user_edit, name="user_edit"),

]
