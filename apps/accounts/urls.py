from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
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
