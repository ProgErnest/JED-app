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
    path(
        "<slug:activity_slug>/ventes/<int:pk>/annuler/",
        views.SaleCancellationCreateView.as_view(),
        name="sale_cancel",
    ),
    path(
        "<slug:activity_slug>/annulations/",
        views.SaleCancellationListView.as_view(),
        name="sale_cancellation_list",
    ),
    path(
        "<slug:activity_slug>/annulations/<int:pk>/",
        views.SaleCancellationDetailView.as_view(),
        name="sale_cancellation_detail",
    ),
]
