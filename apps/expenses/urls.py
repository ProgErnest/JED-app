from django.urls import path

from .views import (
    ExpenseCancelView,
    ExpenseCategoryListView,
    ExpenseCreateView,
    ExpenseDetailView,
    ExpenseListView,
    ExpenseUpdateView,
)

app_name = "expenses"

urlpatterns = [
    path("", ExpenseListView.as_view(), name="expense-list"),
    path("new/", ExpenseCreateView.as_view(), name="expense-create"),
    path("<int:pk>/", ExpenseDetailView.as_view(), name="expense-detail"),
    path("<int:pk>/correct/", ExpenseUpdateView.as_view(), name="expense-edit"),
    path("<int:pk>/cancel/", ExpenseCancelView.as_view(), name="expense-cancel"),
    path("categories/", ExpenseCategoryListView.as_view(), name="category-list"),
]
