from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db.models import (
    Count,
    DecimalField,
    Exists,
    ExpressionWrapper,
    F,
    Max,
    OuterRef,
    Q,
    Subquery,
    Sum,
)

from apps.accounts.permissions import (
    get_accessible_activities,
    user_has_activity_access,
    user_is_employee_in_activity,
    user_is_global,
)
from apps.activities.models import Activity
from apps.catalog.models import CatalogCategory, Product
from apps.sales.models import Sale, SaleCancellation, SaleLine
from apps.inventory.models import StockMovement

ZERO = Decimal("0.00")


def dashboard_metrics(user, activity, start_date: date, end_date: date) -> dict:
    """Return scoped metrics for one activity and inclusive date range."""
    if not user_has_activity_access(user, activity):
        raise PermissionDenied("Accès non autorisé à cette activité.")
    sales = Sale.objects.filter(
        activity=activity,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).exclude(pk__in=SaleCancellation.objects.values("sale_id"))
    # Neutraliser les dépenses dans les indicateurs
    employee_scope = user_is_employee_in_activity(user, activity)
    if employee_scope:
        sales = sales.filter(user=user)
    sale_totals = sales.aggregate(
        revenue=Sum("total"),
        sale_count=Count("pk"),
    )
    lines = SaleLine.objects.filter(sale__in=sales)
    line_totals = lines.aggregate(
        product_revenue=Sum("total", filter=Q(product__isnull=False)),
        service_revenue=Sum("total", filter=Q(service__isnull=False)),
        product_line_count=Count("pk", filter=Q(product__isnull=False)),
        service_line_count=Count("pk", filter=Q(service__isnull=False)),
    )
    reliable_lines = lines.filter(margin_reliable=True, product__isnull=False)
    line_margin = ExpressionWrapper(
        (F("unit_price") - F("cost")) * F("quantity"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    margin_total = reliable_lines.aggregate(margin=Sum(line_margin))["margin"] or ZERO
    unreliable_line_count = lines.filter(
        product__isnull=False,
        margin_reliable=False,
    ).count()
    product_line_count = lines.filter(product__isnull=False).count()
    reliable_product_line_count = reliable_lines.count()
    return {
        "revenue": sale_totals["revenue"] or ZERO,
        "sale_count": sale_totals["sale_count"],
        "product_revenue": line_totals["product_revenue"] or ZERO,
        "service_revenue": line_totals["service_revenue"] or ZERO,
        "product_line_count": line_totals["product_line_count"],
        "service_line_count": line_totals["service_line_count"],
        "expenses": ZERO,
        "expense_count": 0,
        "estimated_margin": margin_total,
        "unreliable_line_count": unreliable_line_count,
        "product_line_count": product_line_count,
        "reliable_margin_line_count": reliable_product_line_count,
        "margin_coverage_percent": (
            reliable_product_line_count / product_line_count * 100
            if product_line_count
            else None
        ),
        "employee_scope": employee_scope,
        "reported_balance": sale_totals["revenue"] or ZERO,
    }


def global_activity_metrics(user, start_date: date, end_date: date) -> list[dict]:
    if not user_is_global(user):
        raise PermissionDenied("Cette vue est réservée au gérant global.")
    activities = Activity.objects.filter(is_active=True).order_by("name")
    rows = []
    for activity in activities:
        metrics = dashboard_metrics(user, activity, start_date, end_date)
        stock_purchase_totals = StockMovement.objects.filter(
            activity=activity,
            movement_type=StockMovement.MovementType.ENTRY,
            unit_cost__isnull=False,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).aggregate(
            count=Count("pk"),
            total=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_cost"),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                )
            )
        )
        rows.append(
            {
                "activity": activity,
                **metrics,
                "stock_purchases": stock_purchase_totals["total"] or ZERO,
                "stock_purchase_count": stock_purchase_totals["count"],
            }
        )
    return rows


def global_item_metrics(user, start_date: date, end_date: date) -> dict:
    """Return global item rankings without treating service revenue as margin."""
    if not user_is_global(user):
        raise PermissionDenied("Cette vue est réservée au gérant global.")
    line_margin = ExpressionWrapper(
        (F("unit_price") - F("cost")) * F("quantity"),
        output_field=DecimalField(max_digits=16, decimal_places=2),
    )
    lines = SaleLine.objects.filter(
        sale__activity__is_active=True,
        sale__created_at__date__gte=start_date,
        sale__created_at__date__lte=end_date,
        sale__cancellation__isnull=True,
    ).annotate(line_margin=line_margin).values(
        "product_id",
        "product__name",
        "service_id",
        "service__name",
        "sale__activity__name",
        "quantity",
        "total",
        "margin_reliable",
        "line_margin",
    )
    grouped = {}
    for row in lines:
        is_product = row["product_id"] is not None
        item_id = row["product_id"] or row["service_id"]
        key = (item_id, row["sale__activity__name"])
        item = grouped.setdefault(
            key,
            {
                "name": row["product__name"] or row["service__name"] or "Article supprimé",
                "activity": row["sale__activity__name"],
                "kind": "product" if is_product else "service",
                "quantity": 0,
                "revenue": ZERO,
                "reliable_line_count": 0,
                "reliable_margin": ZERO if is_product else None,
            },
        )
        item["quantity"] += row["quantity"]
        item["revenue"] += row["total"]
        if is_product and row["margin_reliable"]:
            item["reliable_line_count"] += 1
            item["reliable_margin"] += row["line_margin"] or ZERO
    items = list(grouped.values())
    for item in items:
        if item["kind"] == "product" and not item["reliable_line_count"]:
            item["reliable_margin"] = None
    reliable_products = [
        item for item in items
        if item["kind"] == "product" and item["reliable_margin"] is not None
    ]
    return {
        "best_sellers": sorted(
            items,
            key=lambda item: (item["revenue"], item["quantity"]),
            reverse=True,
        )[:5],
        "profitable_products": sorted(
            reliable_products,
            key=lambda item: item["reliable_margin"],
            reverse=True,
        )[:5],
        "low_margin_products": sorted(
            reliable_products,
            key=lambda item: item["reliable_margin"],
        )[:5],
    }


def global_employee_metrics(user, start_date: date, end_date: date) -> list[dict]:
    """Aggregate operational activity by employee and activity for the period."""
    if not user_is_global(user):
        raise PermissionDenied("Cette vue est réservée au gérant global.")

    activities = Activity.objects.filter(is_active=True)
    canceled_sales = SaleCancellation.objects.values("sale_id")
    grouped = {}

    sales = (
        Sale.objects.filter(
            activity__in=activities,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .exclude(pk__in=canceled_sales)
        .values(
            "activity_id",
            "activity__name",
            "user_id",
            "user__username",
            "user__first_name",
            "user__last_name",
        )
        .annotate(
            sale_count=Count("pk"),
            revenue=Sum("total"),
            last_operation=Max("created_at"),
        )
    )
    for row in sales:
        key = (row["activity_id"], row["user_id"])
        grouped[key] = {
            "activity": row["activity__name"],
            "username": row["user__username"],
            "full_name": " ".join(
                part for part in (row["user__first_name"], row["user__last_name"]) if part
            ) or row["user__username"],
            "sale_count": row["sale_count"],
            "revenue": row["revenue"] or ZERO,
            "expense_count": 0,
            "expenses": ZERO,
            "stock_purchases": ZERO,
            "last_operation": row["last_operation"],
        }

    movements = (
        StockMovement.objects.filter(
            activity__in=activities,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .values(
            "activity_id",
            "activity__name",
            "user_id",
            "user__username",
            "user__first_name",
            "user__last_name",
        )
        .annotate(last_operation=Max("created_at"))
    )
    for row in movements:
        key = (row["activity_id"], row["user_id"])
        employee = grouped.setdefault(
            key,
            {
                "activity": row["activity__name"],
                "username": row["user__username"],
                "full_name": " ".join(
                    part for part in (row["user__first_name"], row["user__last_name"]) if part
                ) or row["user__username"],
                "sale_count": 0,
                "revenue": ZERO,
                "expense_count": 0,
                "expenses": ZERO,
                "stock_purchases": ZERO,
                "last_operation": row["last_operation"],
            },
        )
        employee["last_operation"] = max(
            employee["last_operation"], row["last_operation"]
        )

    stock_purchase_rows = (
        StockMovement.objects.filter(
            activity__in=activities,
            movement_type=StockMovement.MovementType.ENTRY,
            unit_cost__isnull=False,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .values(
            "activity_id",
            "activity__name",
            "user_id",
            "user__username",
            "user__first_name",
            "user__last_name",
        )
        .annotate(
            stock_purchases=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_cost"),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                )
            ),
            last_operation=Max("created_at"),
        )
    )
    for row in stock_purchase_rows:
        key = (row["activity_id"], row["user_id"])
        employee = grouped.setdefault(
            key,
            {
                "activity": row["activity__name"],
                "username": row["user__username"],
                "full_name": " ".join(
                    part for part in (row["user__first_name"], row["user__last_name"]) if part
                ) or row["user__username"],
                "sale_count": 0,
                "revenue": ZERO,
                "expense_count": 0,
                "expenses": ZERO,
                "stock_purchases": ZERO,
                "last_operation": row["last_operation"],
            },
        )
        employee["stock_purchases"] = row["stock_purchases"] or ZERO
        employee["last_operation"] = max(employee["last_operation"], row["last_operation"])

    recent_events = (
        SaleCancellation.objects.filter(
            sale__activity__in=activities,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .values(
            "sale__activity_id",
            "sale__activity__name",
            "user_id",
            "user__username",
            "user__first_name",
            "user__last_name",
        )
        .annotate(last_operation=Max("created_at"))
    )
    for row in recent_events:
        activity_id = row["sale__activity_id"]
        activity_name = row["sale__activity__name"]
        key = (activity_id, row["user_id"])
        employee = grouped.get(key)
        if employee:
            employee["last_operation"] = max(employee["last_operation"], row["last_operation"])
        else:
            grouped[key] = {
                "activity": activity_name,
                "username": row["user__username"],
                "full_name": " ".join(
                    part for part in (row["user__first_name"], row["user__last_name"]) if part
                ) or row["user__username"],
                "sale_count": 0,
                "revenue": ZERO,
                "expense_count": 0,
                "expenses": ZERO,
                "stock_purchases": ZERO,
                "last_operation": row["last_operation"],
            }

    return sorted(
        grouped.values(),
        key=lambda employee: (
            employee["last_operation"],
            employee["activity"],
            employee["full_name"].casefold(),
        ),
        reverse=True,
    )


def activity_dashboard_metrics(user, activity_slug: str, start_date: date, end_date: date) -> tuple[Activity, dict]:
    activity = Activity.objects.filter(slug=activity_slug, is_active=True).first()
    if activity is None or not user_has_activity_access(user, activity):
        raise PermissionDenied("Accès non autorisé à cette activité.")
    return activity, dashboard_metrics(user, activity, start_date, end_date)


def activity_operational_details(user, activity, start_date: date, end_date: date) -> dict:
    """Return period details while keeping employee records author-scoped."""
    if not user_has_activity_access(user, activity):
        raise PermissionDenied("Accès non autorisé à cette activité.")

    sales = Sale.objects.filter(
        activity=activity,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).annotate(
        _is_canceled=Exists(
            SaleCancellation.objects.filter(sale_id=OuterRef("pk"))
        )
    ).select_related("user").prefetch_related("lines__product", "lines__service")
    movements = StockMovement.objects.filter(
        activity=activity,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).select_related("product", "user")

    if user_is_employee_in_activity(user, activity):
        sales = sales.filter(user=user)
        movements = movements.filter(user=user)
    stock_purchase_totals = movements.filter(
        movement_type=StockMovement.MovementType.ENTRY,
        unit_cost__isnull=False,
    ).aggregate(
        amount=Sum(
            ExpressionWrapper(
                F("quantity") * F("unit_cost"),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            )
        ),
        movement_count=Count("pk"),
    )

    sales = sales.order_by("-created_at")[:30]
    movements = movements.order_by("-created_at")[:30]

    sales_by_item = (
        SaleLine.objects.filter(
            sale__activity=activity,
            sale__created_at__date__gte=start_date,
            sale__created_at__date__lte=end_date,
        )
        .exclude(sale__cancellation__isnull=False)
        .values("product__name", "service__name")
        .annotate(quantity=Sum("quantity"), revenue=Sum("total"))
        .order_by("-revenue")
    )
    employee_scope = user_is_employee_in_activity(user, activity)
    if employee_scope:
        sales_by_item = sales_by_item.filter(sale__user=user)

    product_lines = SaleLine.objects.filter(
        sale__activity=activity,
        sale__created_at__date__gte=start_date,
        sale__created_at__date__lte=end_date,
        sale__cancellation__isnull=True,
        product__isnull=False,
    ).select_related("product", "product__category")
    if employee_scope:
        product_lines = product_lines.filter(sale__user=user)

    category_totals = {}
    product_totals = {}
    for line in product_lines:
        category_key = line.category_id_snapshot
        category = category_totals.setdefault(
            category_key,
            {
                "id": category_key,
                "name": line.category_name_snapshot or "Non classés",
                "quantity": 0,
                "revenue": ZERO,
                "product_ids": set(),
                "reliable_line_count": 0,
                "reliable_revenue": ZERO,
                "reliable_margin": ZERO,
                "unknown_cost_line_count": 0,
                "unreliable_cost_line_count": 0,
            },
        )
        product_key = line.product_id
        product = product_totals.setdefault(
            (category_key, product_key),
            {
                "id": product_key,
                "name": line.product.name if line.product_id else "Produit supprimé",
                "category_id": category_key,
                "category_name": category["name"],
                "quantity": 0,
                "revenue": ZERO,
                "reliable_line_count": 0,
                "reliable_revenue": ZERO,
                "reliable_margin": ZERO,
            },
        )
        category["quantity"] += line.quantity
        category["revenue"] += line.total
        category["product_ids"].add(product_key)
        product["quantity"] += line.quantity
        product["revenue"] += line.total
        if line.margin_reliable and line.cost is not None:
            margin = (line.unit_price - line.cost) * line.quantity
            category["reliable_line_count"] += 1
            category["reliable_revenue"] += line.total
            category["reliable_margin"] += margin
            product["reliable_line_count"] += 1
            product["reliable_revenue"] += line.total
            product["reliable_margin"] += margin
        elif line.cost is None:
            category["unknown_cost_line_count"] += 1
        else:
            category["unreliable_cost_line_count"] += 1

    for catalog_category in CatalogCategory.objects.filter(
        activity=activity,
        is_active=True,
    ):
        category_totals.setdefault(
            catalog_category.pk,
            {
                "id": catalog_category.pk,
                "name": catalog_category.name,
                "quantity": 0,
                "revenue": ZERO,
                "product_ids": set(),
                "reliable_line_count": 0,
                "reliable_revenue": ZERO,
                "reliable_margin": ZERO,
                "unknown_cost_line_count": 0,
                "unreliable_cost_line_count": 0,
            },
        )

    current_stock_by_category = {}
    for product in Product.objects.filter(activity=activity).select_related("category"):
        category_key = product.category_id
        stock = current_stock_by_category.setdefault(
            category_key,
            {"stock_quantity": 0, "catalog_product_count": 0},
        )
        stock["stock_quantity"] += product.stock_quantity
        stock["catalog_product_count"] += 1

    product_rankings = []
    products_by_category = {}
    for product in product_totals.values():
        product["reliable_margin_rate"] = (
            product["reliable_margin"] / product["reliable_revenue"] * 100
            if product["reliable_revenue"]
            else None
        )
        product_rankings.append(product)
        products_by_category.setdefault(product["category_id"], []).append(product)
    total_product_revenue = sum(
        (category["revenue"] for category in category_totals.values()),
        start=ZERO,
    )
    category_rankings = []
    for category in category_totals.values():
        category["product_count"] = len(category.pop("product_ids"))
        category["revenue_share_percent"] = (
            category["revenue"] / total_product_revenue * 100
            if total_product_revenue
            else 0
        )
        category["reliable_margin_rate"] = (
            category["reliable_margin"] / category["reliable_revenue"] * 100
            if category["reliable_revenue"]
            else None
        )
        category.update(
            current_stock_by_category.get(
                category["id"],
                {"stock_quantity": 0, "catalog_product_count": 0},
            )
        )
        category["products"] = sorted(
            products_by_category.get(category["id"], []),
            key=lambda product: (product["revenue"], product["quantity"]),
            reverse=True,
        )[:3]
        category_rankings.append(category)
    product_rankings.sort(
        key=lambda product: (product["revenue"], product["quantity"]),
        reverse=True,
    )
    category_rankings.sort(
        key=lambda category: (category["revenue"], category["quantity"]),
        reverse=True,
    )

    product_sales = Q(
        sale_lines__sale__created_at__date__gte=start_date,
        sale_lines__sale__created_at__date__lte=end_date,
        sale_lines__sale__cancellation__isnull=True,
    )
    reliable_product_sales = product_sales & Q(sale_lines__margin_reliable=True)
    last_sales = SaleLine.objects.filter(
        product_id=OuterRef("pk"),
        sale__activity=activity,
    ).exclude(sale__cancellation__isnull=False)
    if employee_scope:
        product_sales &= Q(sale_lines__sale__user=user)
        reliable_product_sales &= Q(sale_lines__sale__user=user)
        last_sales = last_sales.filter(sale__user=user)

    product_rows = Product.objects.filter(activity=activity).annotate(
        sold_line_count=Count("sale_lines__pk", filter=product_sales),
        sold_quantity=Sum("sale_lines__quantity", filter=product_sales),
        revenue=Sum("sale_lines__total", filter=product_sales),
        reliable_line_count=Count("sale_lines__pk", filter=reliable_product_sales),
        reliable_revenue=Sum("sale_lines__total", filter=reliable_product_sales),
        reliable_cogs=Sum(
            ExpressionWrapper(
                F("sale_lines__cost") * F("sale_lines__quantity"),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            ),
            filter=reliable_product_sales,
        ),
        reliable_margin=Sum(
            ExpressionWrapper(
                (F("sale_lines__unit_price") - F("sale_lines__cost"))
                * F("sale_lines__quantity"),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            ),
            filter=reliable_product_sales,
        ),
        unknown_cost_line_count=Count(
            "sale_lines__pk",
            filter=product_sales & Q(sale_lines__cost__isnull=True),
        ),
        unreliable_cost_line_count=Count(
            "sale_lines__pk",
            filter=product_sales
            & Q(sale_lines__cost__isnull=False, sale_lines__margin_reliable=False),
        ),
        last_sale_at=Subquery(last_sales.order_by("-sale__created_at").values("sale__created_at")[:1]),
    ).order_by("name")
    product_profitability = []
    for product in product_rows:
        has_reliable_sales = product.reliable_line_count > 0
        reliable_revenue = product.reliable_revenue if has_reliable_sales else None
        reliable_margin = product.reliable_margin if has_reliable_sales else None
        product_profitability.append(
            {
                "product": product,
                "sold_line_count": product.sold_line_count,
                "quantity": product.sold_quantity or 0,
                "revenue": product.revenue or ZERO,
                "reliable_line_count": product.reliable_line_count,
                "reliable_revenue": reliable_revenue,
                "reliable_cogs": product.reliable_cogs if has_reliable_sales else None,
                "reliable_margin": reliable_margin,
                "reliable_margin_rate": (
                    reliable_margin / reliable_revenue * 100
                    if reliable_revenue
                    else None
                ),
                "unknown_cost_line_count": product.unknown_cost_line_count,
                "unreliable_cost_line_count": product.unreliable_cost_line_count,
                "last_sale_at": product.last_sale_at,
            }
        )

    # Neutraliser les dépenses et audits dans le contexte
    return {
        "sales": sales,
        "expenses": [],
        "movements": movements,
        "sales_by_item": sales_by_item,
        "category_rankings": category_rankings,
        "category_product_rankings": product_rankings,
        "product_profitability": product_profitability,
        "expenses_by_category": [],
        "stock_purchase_total": stock_purchase_totals["amount"] or ZERO,
        "stock_purchase_count": stock_purchase_totals["movement_count"],
        "expense_audits": [],
    }


def accessible_dashboard_activities(user):
    return get_accessible_activities(user).filter(is_active=True).order_by("name")
