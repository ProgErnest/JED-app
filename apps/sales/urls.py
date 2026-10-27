from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path(
        "<slug:activity_slug>/ventes/",
        views.SaleListView.as_view(),
        name="sale_list",
    ),
    path(
        "<slug:activity_slug>/ventes/nouvelle/",
        views.SaleCreateView.as_view(),
        name="sale_add",
    ),
    path(
        "<slug:activity_slug>/ventes/<int:pk>/",
        views.SaleDetailView.as_view(),
        name="sale_detail",
    ),
]
