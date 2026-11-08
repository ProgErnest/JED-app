from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.CatalogHomeView.as_view(), name="home"),
    path(
        "<slug:activity_slug>/categories/",
        views.CatalogCategoryListView.as_view(),
        name="category_list",
    ),
    path(
        "<slug:activity_slug>/categories/add/",
        views.CatalogCategoryCreateView.as_view(),
        name="category_add",
    ),
    path(
        "<slug:activity_slug>/categories/<slug:category_slug>/edit/",
        views.CatalogCategoryUpdateView.as_view(),
        name="category_edit",
    ),
    path(
        "<slug:activity_slug>/products/",
        views.ProductListView.as_view(),
        name="product_list",
    ),
    path(
        "<slug:activity_slug>/products/add/",
        views.ProductCreateView.as_view(),
        name="product_add",
    ),
    path(
        "<slug:activity_slug>/products/<slug:slug>/edit/",
        views.ProductUpdateView.as_view(),
        name="product_edit",
    ),
    path(
        "<slug:activity_slug>/services/",
        views.ServiceListView.as_view(),
        name="service_list",
    ),
    path(
        "<slug:activity_slug>/services/add/",
        views.ServiceCreateView.as_view(),
        name="service_add",
    ),
    path(
        "<slug:activity_slug>/services/<slug:slug>/edit/",
        views.ServiceUpdateView.as_view(),
        name="service_edit",
    ),
]
