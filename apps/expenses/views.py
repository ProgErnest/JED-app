from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, ListView, UpdateView
from django.views.generic.edit import CreateView, FormView

from apps.accounts.permissions import UserCanAccessActivityMixin, user_is_employee_in_activity

from .forms import ExpenseCancelForm, ExpenseCorrectionForm, ExpenseForm
from .models import Expense, ExpenseAuditLog


class ExpenseListView(LoginRequiredMixin, UserCanAccessActivityMixin, ListView):
    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"
    paginate_by = 20

    def get_queryset(self):
        activity = self.get_activity_from_request()
        queryset = Expense.objects.filter(activity=activity)
        if user_is_employee_in_activity(self.request.user, activity):
            queryset = queryset.filter(user=self.request.user)
        return queryset.select_related(
            "category",
            "user",
            "activity",
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity_from_request()
        return context


class ExpenseCreateView(LoginRequiredMixin, UserCanAccessActivityMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["activity"] = self.get_activity_from_request()
        return kwargs

    def form_valid(self, form):
        expense = form.save(commit=False)
        expense.activity = self.get_activity_from_request()
        expense.user = self.request.user
        expense.save()
        messages.success(self.request, "La dépense a été enregistrée.")
        return redirect(f"{reverse('expenses:expense-list')}?activity={self.get_activity_from_request().slug}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity_from_request()
        return context


class ExpenseDetailView(LoginRequiredMixin, UserCanAccessActivityMixin, DetailView):
    model = Expense
    template_name = "expenses/expense_detail.html"
    context_object_name = "expense"

    def get_queryset(self):
        activity = self.get_activity_from_request()
        queryset = Expense.objects.filter(activity=activity)
        if user_is_employee_in_activity(self.request.user, activity):
            queryset = queryset.filter(user=self.request.user)
        return queryset.select_related(
            "category",
            "user",
            "activity",
        )


class ExpenseCancelView(LoginRequiredMixin, UserCanAccessActivityMixin, FormView):
    form_class = ExpenseCancelForm
    template_name = "expenses/expense_cancel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["expense"] = self.get_expense()
        context["activity"] = self.get_activity_from_request()
        return context

    def get_expense(self):
        activity = self.get_activity_from_request()
        queryset = Expense.objects.filter(activity=activity, is_canceled=False)
        if user_is_employee_in_activity(self.request.user, activity):
            queryset = queryset.filter(user=self.request.user)
        return get_object_or_404(
            queryset.select_related("category", "user"),
            pk=self.kwargs["pk"],
        )

    def form_valid(self, form):
        expense = self.get_expense()
        with transaction.atomic():
            expense.cancel(form.cleaned_data["reason"], self.request.user)
        messages.success(self.request, "La dépense a été annulée.")
        return redirect(f"{reverse('expenses:expense-list')}?activity={self.get_activity_from_request().slug}")


class ExpenseUpdateView(LoginRequiredMixin, UserCanAccessActivityMixin, UpdateView):
    model = Expense
    form_class = ExpenseCorrectionForm
    template_name = "expenses/expense_form.html"

    def get_queryset(self):
        activity = self.get_activity_from_request()
        queryset = Expense.objects.filter(activity=activity, is_canceled=False)
        if user_is_employee_in_activity(self.request.user, activity):
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["activity"] = self.get_activity_from_request()
        return kwargs

    def form_valid(self, form):
        expense = self.get_object()
        old_amount = expense.amount
        old_category = expense.category.name
        old_description = expense.description
        with transaction.atomic():
            expense = form.save(commit=False)
            expense.save()
            ExpenseAuditLog.objects.create(
                expense=expense,
                user=self.request.user,
                action=ExpenseAuditLog.Action.UPDATED,
                reason=(
                    f"{form.cleaned_data['reason']} "
                    f"Montant : {old_amount} -> {expense.amount}; "
                    f"catégorie : {old_category} -> {expense.category.name}; "
                    f"description : {old_description or '-'} -> {expense.description or '-'}"
                ),
            )
        messages.success(self.request, "La dépense a été mise à jour.")
        return redirect(
            f"{reverse('expenses:expense-detail', kwargs={'pk': expense.pk})}?activity={self.get_activity_from_request().slug}"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity_from_request()
        return context


class ExpenseCategoryListView(LoginRequiredMixin, UserCanAccessActivityMixin, ListView):
    model = ExpenseAuditLog
    template_name = "expenses/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        activity = self.get_activity_from_request()
        return activity.expense_categories.all().order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity_from_request()
        return context
