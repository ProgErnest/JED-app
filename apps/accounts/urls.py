from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="accounts:login"),
        name="logout",
    ),
    path("", views.home, name="home"),
    path(
        "activite/<slug:activity_slug>/",
        views.activity_detail,
        name="activity_detail",
    ),
    path(
        "activite/<slug:activity_slug>/gerer/",
        views.activity_manage,
        name="activity_manage",
    ),
    path(
        "cbv/liste/",
        views.ActivityListView.as_view(),
        name="activity_list_cbv",
    ),
    path(
        "cbv/activite/<slug:activity_slug>/",
        views.ActivityAccessCBVView.as_view(),
        name="activity_access_cbv",
    ),
]
