from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.InventoryHomeView.as_view(), name="home"),
    path(
        "<slug:activity_slug>/mouvements/",
        views.StockMovementListView.as_view(),
        name="movement_list",
    ),
    path(
        "<slug:activity_slug>/stock/<slug:product_slug>/",
        views.ProductStockDetailView.as_view(),
        name="product_stock_detail",
    ),
    path(
        "<slug:activity_slug>/mouvements/entree/",
        views.StockEntryCreateView.as_view(),
        name="movement_entry_add",
    ),
    path(
        "<slug:activity_slug>/mouvements/correction/",
        views.StockCorrectionCreateView.as_view(),
        name="movement_correction_add",
    ),
]
