from __future__ import annotations

import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity
from apps.catalog.models import Product, Service
from apps.expenses.models import Expense, ExpenseCategory
from apps.inventory.models import StockMovement
from apps.inventory.services import record_stock_movement
from apps.sales.models import Sale, SaleCancellation
from apps.sales.services import cancel_sale, create_sale


SEED_PREFIX = "demo-jed-"
USER_PREFIX = "demo_jed_"
DEMO_PASSWORD = "DemoJED2026!"
WEEKS = 8

PRODUCTS = {
    "boutique": [
        ("Huile de palme raffinée 1 L", "huile-palme-1l", "bouteille", "1800", "2300"),
        ("Riz parfumé 5 kg", "riz-parfume-5kg", "sac", "3000", "3750"),
        ("Sucre en poudre 1 kg", "sucre-1kg", "paquet", "750", "1000"),
        ("Savon de ménage", "savon-menage", "pièce", "350", "500"),
        ("Lait en poudre 400 g", "lait-poudre-400g", "boîte", "2300", "2900"),
        ("Tomate concentrée 400 g", "tomate-400g", "boîte", "450", "650"),
        ("Spaghetti 500 g", "spaghetti-500g", "paquet", "450", "650"),
        ("Eau minérale 1,5 L", "eau-minerale-15l", "bouteille", "300", "500"),
        ("Biscuit familial", "biscuit-familial", "paquet", "300", "500"),
    ],
    "restaurant-bar": [
        ("Bière blonde 33 cl", "biere-blonde-33cl", "bouteille", "550", "800"),
        ("Bière blonde 65 cl", "biere-blonde-65cl", "bouteille", "950", "1300"),
        ("Eau minérale 1,5 L", "eau-minerale-15l", "bouteille", "350", "700"),
        ("Boisson gazeuse 50 cl", "boisson-gazeuse-50cl", "bouteille", "450", "800"),
        ("Jus de fruits 1 L", "jus-fruits-1l", "bouteille", "900", "1500"),
        ("Boisson énergisante", "boisson-energisante", "canette", "700", "1200"),
        ("Eau en sachet", "eau-sachet", "sachet", "20", "50"),
        ("Arachides grillées", "arachides-grillees", "portion", "250", "500"),
    ],
    "coiffure": [
        ("Mèches synthétiques classiques", "meches-classiques", "paquet", "2200", "3500"),
        ("Mèches brésiliennes", "meches-bresiliennes", "paquet", "9000", "13000"),
        ("Shampooing professionnel 500 ml", "shampooing-500ml", "flacon", "3000", "4500"),
        ("Gel coiffant", "gel-coiffant", "pot", "1200", "2000"),
        ("Huile capillaire", "huile-capillaire", "flacon", "1800", "3000"),
        ("Bonnet de nuit en satin", "bonnet-satin", "pièce", "1500", "2500"),
    ],
}

SERVICES = {
    "boutique": [
        ("Photocopie noir et blanc A4", "photocopie-a4", "50", 2),
        ("Impression couleur A4", "impression-couleur", "500", 5),
    ],
    "restaurant-bar": [
        ("Service traiteur, réservation", "service-traiteur", "25000", 60),
        ("Livraison de proximité", "livraison-proximite", "1500", 30),
    ],
    "coiffure": [
        ("Tresses simples", "tresses-simples", "8000", 120),
        ("Tresses avec mèches", "tresses-avec-meches", "15000", 240),
        ("Coupe et brushing", "coupe-brushing", "5000", 60),
        ("Défrisage et soin", "defrisage-soin", "10000", 120),
        ("Pose de perruque", "pose-perruque", "7000", 60),
    ],
}

TEAM = {
    "boutique": [
        ("manager", "Clarisse", "Mbarga"),
        ("staff_a", "Serge", "Tchinda"),
        ("staff_b", "Nadia", "Ekotto"),
    ],
    "restaurant-bar": [
        ("manager", "Alain", "Mballa"),
        ("staff_a", "Brice", "Ngono"),
        ("staff_b", "Chantal", "Fouda"),
    ],
    "coiffure": [
        ("manager", "Mireille", "Ewane"),
        ("staff_a", "Ariane", "Biloa"),
        ("staff_b", "Fabrice", "Nkom"),
    ],
}

EXPENSE_CATEGORIES = {
    "boutique": ["Transport et livraison", "Électricité ENEO", "Loyer", "Petites fournitures"],
    "restaurant-bar": ["Approvisionnement marché", "Gaz de cuisine", "Électricité ENEO", "Transport"],
    "coiffure": ["Électricité ENEO", "Loyer", "Transport", "Produits d'entretien"],
}


class Command(BaseCommand):
    help = "Ajoute huit semaines de données synthétiques de démonstration JED."

    def handle(self, *args, **options):
        randomizer = random.Random(20261103)
        today = timezone.localdate()
        first_day = today - timedelta(days=WEEKS * 7 - 1)

        with transaction.atomic():
            activities = {
                activity.slug: activity
                for activity in Activity.objects.filter(slug__in=PRODUCTS)
            }
            if set(activities) != set(PRODUCTS):
                missing = sorted(set(PRODUCTS) - set(activities))
                raise CommandError(f"Activités initiales manquantes : {', '.join(missing)}")

            users = self._get_team(activities)
            products, services = self._get_catalog(activities)
            categories = self._get_expense_categories(activities)
            self._clear_previous_seed(users, products)
            self._create_history(activities, users, products, services, categories, first_day, today, randomizer)

        self.stdout.write(self.style.SUCCESS(
            f"Données JED ajoutées du {first_day:%d/%m/%Y} au {today:%d/%m/%Y} "
            f"({Sale.objects.filter(user__username__startswith=USER_PREFIX).count()} ventes, "
            f"{StockMovement.objects.filter(product__slug__startswith=SEED_PREFIX).count()} mouvements, "
            f"{Expense.objects.filter(user__username__startswith=USER_PREFIX).count()} dépenses)."
        ))
        self.stdout.write(f"Comptes de démonstration : mot de passe commun {DEMO_PASSWORD}")

    def _get_team(self, activities):
        users = {}
        global_user, _ = User.objects.get_or_create(
            username=f"{USER_PREFIX}gerant",
            defaults={"first_name": "Étienne", "last_name": "Nsame", "email": "gerant@demo.jed.example.test"},
        )
        if not global_user.has_usable_password():
            global_user.set_password(DEMO_PASSWORD)
            global_user.save(update_fields=["password"])
        global_user.set_password(DEMO_PASSWORD)
        global_user.save(update_fields=["password"])
        ActivityMembership.objects.get_or_create(user=global_user, activity=None, defaults={"role": Role.GLOBAL})
        users["global"] = global_user

        for slug, team in TEAM.items():
            users[slug] = {}
            for role_key, first_name, last_name in team:
                username = f"{USER_PREFIX}{slug.replace('-', '_')}_{role_key}"
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": f"{username}@demo.jed.example.test",
                    },
                )
                if created:
                    user.set_password(DEMO_PASSWORD)
                    user.save(update_fields=["password"])
                role = Role.MANAGER if role_key == "manager" else Role.EMPLOYEE
                ActivityMembership.objects.get_or_create(
                    user=user,
                    activity=activities[slug],
                    defaults={"role": role, "is_active": True},
                )
                users[slug][role_key] = user
        return users

    def _get_catalog(self, activities):
        products, services = {}, {}
        for slug, entries in PRODUCTS.items():
            activity = activities[slug]
            products[slug] = []
            for name, token, unit, cost, price in entries:
                product, _ = Product.objects.update_or_create(
                    activity=activity,
                    slug=f"{SEED_PREFIX}{slug}-{token}",
                    defaults={
                        "name": name,
                        "unit": unit,
                        "description": f"Article courant vendu en FCFA, sélectionné pour le jeu de démonstration {activity.name}.",
                        "price": Decimal(price),
                        "is_active": True,
                        "stock_quantity": 0,
                        "average_cost": Decimal("0"),
                    },
                )
                products[slug].append((product, Decimal(cost)))

            services[slug] = []
            for name, token, price, duration in SERVICES[slug]:
                service, _ = Service.objects.update_or_create(
                    activity=activity,
                    slug=f"{SEED_PREFIX}{slug}-{token}",
                    defaults={
                        "name": name,
                        "description": "Tarif indicatif en FCFA pour les données synthétiques.",
                        "price": Decimal(price),
                        "duration_minutes": duration,
                        "is_active": True,
                    },
                )
                services[slug].append(service)
        return products, services

    def _get_expense_categories(self, activities):
        categories = {}
        for slug, names in EXPENSE_CATEGORIES.items():
            categories[slug] = []
            for name in names:
                category, _ = ExpenseCategory.objects.get_or_create(
                    activity=activities[slug],
                    slug=f"{SEED_PREFIX}{slug}-{name.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e')}"[:120],
                    defaults={"name": name, "description": "Catégorie de démonstration."},
                )
                categories[slug].append(category)
        return categories

    def _clear_previous_seed(self, users, products):
        seed_user_ids = [user.pk for user in users.values() if isinstance(user, User)]
        for team in users.values():
            if isinstance(team, dict):
                seed_user_ids.extend(user.pk for user in team.values())
        seed_products = [product for rows in products.values() for product, _ in rows]
        SaleCancellation.objects.filter(sale__user_id__in=seed_user_ids).delete()
        Sale.objects.filter(user_id__in=seed_user_ids).delete()
        StockMovement.objects.filter(product__in=seed_products).delete()
        Expense.objects.filter(user_id__in=seed_user_ids).delete()
        Product.objects.filter(pk__in=[product.pk for product in seed_products]).update(
            stock_quantity=0,
            average_cost=Decimal("0"),
        )

    def _create_history(self, activities, users, products, services, categories, first_day, today, randomizer):
        for slug, rows in products.items():
            activity = activities[slug]
            manager = users[slug]["manager"]
            for product, unit_cost in rows:
                record_stock_movement(
                    product=product,
                    movement_type=StockMovement.MovementType.ENTRY,
                    quantity=120 if slug != "coiffure" else 35,
                    unit_cost=unit_cost,
                    user=manager,
                    reason="Approvisionnement initial chez un grossiste local",
                    activity=activity,
                )
                self._set_date(product._last_stock_movement, first_day, randomizer)

        for day_index in range(WEEKS * 7):
            day = first_day + timedelta(days=day_index)
            for slug, activity in activities.items():
                rows = products[slug]
                manager = users[slug]["manager"]
                team = users[slug]

                if day_index and day_index % 7 in (1, 4):
                    product, cost = randomizer.choice(rows)
                    quantity = randomizer.randint(35, 90) if slug != "coiffure" else randomizer.randint(12, 30)
                    record_stock_movement(
                        product=product,
                        movement_type=StockMovement.MovementType.ENTRY,
                        quantity=quantity,
                        unit_cost=cost,
                        user=manager,
                        reason=randomizer.choice(("Achat au marché de gros", "Réapprovisionnement fournisseur", "Livraison hebdomadaire")),
                        activity=activity,
                    )
                    self._set_date(product._last_stock_movement, day, randomizer)

                if day_index % 7 == 5:
                    product, _ = randomizer.choice(rows)
                    counted = max(0, product.stock_quantity + randomizer.choice((-2, -1, 1, 2)))
                    record_stock_movement(
                        product=product,
                        movement_type=StockMovement.MovementType.CORRECTION,
                        counted_quantity=counted,
                        user=manager,
                        reason=randomizer.choice(("Comptage physique de fin de semaine", "Casse constatée au rangement", "Écart de comptage après inventaire")),
                        activity=activity,
                    )
                    if product._last_stock_movement:
                        self._set_date(product._last_stock_movement, day, randomizer)

                if day.weekday() == 6 and slug != "restaurant-bar":
                    continue
                count_range = {"boutique": (2, 5), "restaurant-bar": (4, 9), "coiffure": (1, 4)}[slug]
                number_of_sales = randomizer.randint(*count_range)
                for _ in range(number_of_sales):
                    seller = randomizer.choice((team["staff_a"], team["staff_b"], manager))
                    lines = self._sale_lines(slug, rows, services[slug], randomizer)
                    if not lines:
                        continue
                    last_movement_id = (
                        StockMovement.objects.order_by("-pk")
                        .values_list("pk", flat=True)
                        .first()
                        or 0
                    )
                    sale = create_sale(activity, seller, lines)
                    self._set_date(sale, day, randomizer)
                    sale_movement_ids = set(
                        StockMovement.objects.filter(pk__gt=last_movement_id)
                        .values_list("pk", flat=True)
                    )
                    self._set_movement_dates(sale_movement_ids, day, randomizer)
                    if randomizer.random() < 0.012:
                        last_movement_id = (
                            StockMovement.objects.order_by("-pk")
                            .values_list("pk", flat=True)
                            .first()
                            or 0
                        )
                        cancel_sale(sale, manager, "Ticket saisi en double; remboursement effectué")
                        SaleCancellation.objects.filter(sale=sale).update(
                            created_at=self._date_time(day, randomizer)
                        )
                        cancellation_movement_ids = set(
                            StockMovement.objects.filter(pk__gt=last_movement_id)
                            .values_list("pk", flat=True)
                        )
                        self._set_movement_dates(cancellation_movement_ids, day, randomizer)

                if randomizer.random() < 0.48:
                    category = randomizer.choice(categories[slug])
                    amount, description = self._expense_details(slug, category.name, randomizer)
                    expense_user = randomizer.choice((manager, team["staff_a"], team["staff_b"]))
                    expense = Expense.objects.create(
                        activity=activity,
                        category=category,
                        user=expense_user,
                        amount=amount,
                        description=description,
                    )
                    Expense.objects.filter(pk=expense.pk).update(created_at=self._date_time(day, randomizer))
                    if randomizer.random() < 0.015:
                        expense.cancel(expense_user, "Justificatif doublonné, dépense neutralisée")
                        Expense.objects.filter(pk=expense.pk).update(canceled_at=self._date_time(day, randomizer))

    def _sale_lines(self, slug, product_rows, services, randomizer):
        lines = []
        service_chance = {"boutique": 0.05, "restaurant-bar": 0.08, "coiffure": 0.78}[slug]
        line_count = randomizer.randint(1, 3)
        for _ in range(line_count):
            if randomizer.random() < service_chance and services:
                item = randomizer.choice(services)
            else:
                item, _ = randomizer.choice(product_rows)
                if item.stock_quantity < 1:
                    continue
            quantity = 1 if slug == "coiffure" else randomizer.choices((1, 2, 3, 4), weights=(65, 24, 8, 3))[0]
            if hasattr(item, "stock_quantity"):
                quantity = min(quantity, item.stock_quantity)
                if quantity < 1:
                    continue
            lines.append({"item": item, "quantity": quantity})
        return lines

    def _expense_details(self, slug, category, randomizer):
        choices = {
            "Loyer": (("180000", "250000"), "Loyer mensuel du local, quartier commercial"),
            "Électricité ENEO": (("8000", "35000"), "Recharge du compteur prépayé ENEO"),
            "Gaz de cuisine": (("6500", "12000"), "Bouteille de gaz domestique"),
            "Transport": (("1500", "8000"), "Déplacements en taxi et livraison en moto"),
            "Transport et livraison": (("2000", "10000"), "Transport des achats et livraison client"),
            "Approvisionnement marché": (("5000", "30000"), "Petits achats frais au marché du quartier"),
            "Petites fournitures": (("1000", "7500"), "Sacs, reçus et fournitures du comptoir"),
            "Produits d'entretien": (("1500", "6000"), "Désinfectant, savon et consommables du salon"),
        }
        low_high, description = choices.get(category, (("1500", "9000"), f"Dépense courante : {category.lower()}"))
        amount = Decimal(randomizer.randrange(int(low_high[0]) // 500, int(low_high[1]) // 500 + 1) * 500)
        if category == "Loyer":
            amount = Decimal(randomizer.choice(("180000", "200000", "225000", "250000")))
        return amount, description

    def _set_date(self, instance, day, randomizer):
        timestamp = self._date_time(day, randomizer)
        instance.__class__.objects.filter(pk=instance.pk).update(created_at=timestamp)
        if hasattr(instance, "updated_at"):
            instance.__class__.objects.filter(pk=instance.pk).update(updated_at=timestamp)

    def _set_movement_dates(self, movement_ids, day, randomizer):
        for movement_id in movement_ids:
            StockMovement.objects.filter(pk=movement_id).update(
                created_at=self._date_time(day, randomizer)
            )

    def _date_time(self, day, randomizer):
        hour = randomizer.randint(8, 20)
        minute = randomizer.choice((0, 10, 15, 20, 30, 40, 45, 50))
        return timezone.make_aware(datetime.combine(day, time(hour, minute)))