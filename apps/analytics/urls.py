from django.urls import path

from .views import ActivityDashboardView, DashboardHomeView, GlobalDashboardView

app_name = "analytics"

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="home"),
    path("global/", GlobalDashboardView.as_view(), name="global-dashboard"),
    path("activity/<slug:activity_slug>/", ActivityDashboardView.as_view(), name="activity-dashboard"),
]
