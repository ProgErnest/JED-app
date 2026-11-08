from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity
from apps.inventory.models import StockMovement
from apps.inventory.services import record_stock_movement
from apps.sales.models import SaleLine
from apps.sales.services import create_sale
from apps.catalog.models import Product, Service
from apps.catalog.services import REFERENCE_CATALOG, load_reference_catalog


class Command(BaseCommand):
    help = "Charge des exemples de catalogue tarifés indicatifs sans écraser les données existantes."

    def add_arguments(self, parser):
        parser.add_argument("--activity-slug", choices=sorted(REFERENCE_CATALOG))
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les créations prévues sans écrire en base.",
        )
        parser.add_argument(
            "--include-sales",
            action="store_true",
            help="Ajoute un stock d'ouverture et un ticket de démonstration par activité.",
        )

    def handle(self, *args, **options):
        activity_slugs = [options["activity_slug"]] if options["activity_slug"] else sorted(REFERENCE_CATALOG)
        activities = list(Activity.objects.filter(slug__in=activity_slugs).order_by("slug"))
        if len(activities) != len(activity_slugs):
            found = {activity.slug for activity in activities}
            missing = sorted(set(activity_slugs) - found)
            raise CommandError(f"Activité(s) introuvable(s) : {', '.join(missing)}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Simulation uniquement; aucune écriture en base."))

        with transaction.atomic():
            for activity in activities:
                result = load_reference_catalog(activity, dry_run=options["dry_run"])
                details = {"stock_entries": 0, "sales_created": 0, "sales_skipped": 0}
                if options["include_sales"]:
                    details = self._load_activity_transactions(
                        activity, dry_run=options["dry_run"]
                    )
                self.stdout.write(
                    f"{activity.name}: {result['categories_created']} rubrique(s), "
                    f"{result['products_created']} produit(s), "
                    f"{result['services_created']} prestation(s) à créer; "
                    f"{result['skipped']} élément(s) déjà présent(s); "
                    f"{details['stock_entries']} approvisionnement(s), "
                    f"{details['sales_created']} vente(s) à créer, "
                    f"{details['sales_skipped']} vente(s) déjà présente(s)."
                )

    def _load_activity_transactions(self, activity, *, dry_run):
        products = list(
            Product.objects.filter(activity=activity, slug__startswith="ref-").order_by("slug")
        )
        services = list(
            Service.objects.filter(activity=activity, slug__startswith="ref-").order_by("slug")
        )
        result = {"stock_entries": 0, "sales_created": 0, "sales_skipped": 0}
        manager_membership = ActivityMembership.objects.filter(
            activity=activity, role=Role.MANAGER, is_active=True
        ).select_related("user").first()
        manager = manager_membership.user if manager_membership else None

        planned_products = len(REFERENCE_CATALOG[activity.slug]["products"])
        if dry_run:
            products_by_slug = {product.slug for product in products}
            products_to_create = sum(
                f"ref-{entry[2]}" not in products_by_slug
                for entry in REFERENCE_CATALOG[activity.slug]["products"]
            )
            result["stock_entries"] = sum(
                not StockMovement.objects.filter(
                    product=product,
                    movement_type=StockMovement.MovementType.ENTRY,
                    reason__startswith="Approvisionnement de démonstration des références PDF",
                ).exists()
                for product in products
            ) + products_to_create

        if products and manager is None:
            raise CommandError(
                f"Aucun responsable actif trouvé pour {activity.name}; "
                "créez ou activez son appartenance avant --include-sales."
            )

        for product in products:
            reason = "Approvisionnement de démonstration des références PDF"
            seeded_entry_exists = StockMovement.objects.filter(
                product=product,
                movement_type=StockMovement.MovementType.ENTRY,
                reason__startswith=reason,
            ).exists()
            if seeded_entry_exists:
                continue
            result["stock_entries"] += 1
            if dry_run:
                continue
            estimated_cost = (product.price * Decimal("0.70")).quantize(Decimal("0.01"))
            record_stock_movement(
                product=product,
                movement_type=StockMovement.MovementType.ENTRY,
                quantity=20,
                unit_cost=estimated_cost,
                user=manager,
                reason=reason + " (coût d'achat synthétique, à remplacer par le coût réel)",
                activity=activity,
            )

        if not products and not services and not (dry_run and (planned_products or REFERENCE_CATALOG[activity.slug]["services"])):
            return result

        reference_lines = SaleLine.objects.filter(sale__activity=activity).filter(
            product__slug__startswith="ref-"
        ) | SaleLine.objects.filter(sale__activity=activity).filter(
            service__slug__startswith="ref-"
        )
        if reference_lines.exists():
            result["sales_skipped"] = 1
            return result
        if manager is None:
            raise CommandError(
                f"Aucun responsable actif trouvé pour {activity.name}; "
                "créez ou activez son appartenance avant --include-sales."
            )

        available_product = next(
            (product for product in products if product.stock_quantity >= 1), None
        )
        lines = []
        if available_product:
            lines.append({"item": available_product, "quantity": 1})
        if services:
            lines.append({"item": services[0], "quantity": 1})
        if not lines:
            if dry_run and (planned_products or REFERENCE_CATALOG[activity.slug]["services"]):
                result["sales_created"] = 1
            return result

        if dry_run:
            result["sales_created"] = 1
            return result
        try:
            create_sale(activity=activity, user=manager, lines_data=lines)
        except (ValidationError, ValueError) as exc:
            raise CommandError(f"Impossible de créer la vente de démonstration : {exc}") from exc
        result["sales_created"] = 1
        return result
