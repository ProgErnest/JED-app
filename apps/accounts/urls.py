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
    path("equipe/", views.team_list, name="team_global"),
    path("equipe/nouveau/", views.team_create, name="team_create_global"),
    path("equipe/<int:membership_id>/modifier/", views.team_edit, name="team_edit"),
    path("equipe/<int:membership_id>/desactiver/", views.team_deactivate, name="team_deactivate"),
    path("equipe/compte/<int:user_id>/desactiver/", views.account_deactivate, name="account_deactivate"),
    path("activite/<slug:activity_slug>/equipe/", views.team_list, name="team_activity"),
    path("activite/<slug:activity_slug>/equipe/nouveau/", views.team_create, name="team_create_activity"),
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
