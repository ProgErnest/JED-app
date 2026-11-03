from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity
from apps.catalog.models import PriceHistory, Service


class ServiceManagementViewTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Salon JED", slug="salon-jed")
        self.manager = User.objects.create_user("manager", password="test-password")
        ActivityMembership.objects.create(
            user=self.manager,
            activity=self.activity,
            role=Role.MANAGER,
        )
        self.client.force_login(self.manager)

    def test_product_and_service_lists_link_to_each_other(self):
        Service.objects.create(
            activity=self.activity,
            name="Tresses simples",
            slug="tresses-simples",
            price=Decimal("7500.00"),
            duration_minutes=90,
        )
        product_response = self.client.get(
            reverse("catalog:product_list", args=[self.activity.slug])
        )
        service_response = self.client.get(
            reverse("catalog:service_list", args=[self.activity.slug])
        )

        self.assertContains(product_response, "Prestations")
        self.assertContains(service_response, "Produits")
        self.assertContains(service_response, "Nouvelle prestation")
        self.assertContains(service_response, "Tresses simples")
        rendered_service_page = service_response.content.decode().replace("\xa0", " ")
        self.assertIn("7 500", rendered_service_page)
        self.assertContains(service_response, "90")
        self.assertContains(service_response, "product-card__prices")
        self.assertNotContains(service_response, "Modifié le")
        self.assertNotContains(service_response, "Statut")

    def test_create_form_hides_slug_and_active_fields(self):
        response = self.client.get(
            reverse("catalog:service_add", args=[self.activity.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="price"')
        self.assertNotContains(response, 'name="slug"')
        self.assertNotContains(response, 'name="is_active"')

    def test_create_service_generates_unique_slug_and_defaults_to_active(self):
        create_url = reverse("catalog:service_add", args=[self.activity.slug])
        service_data = {
            "name": "Coupe & coiffure",
            "price": "2500",
            "duration_minutes": "45",
            "description": "",
        }

        response = self.client.post(create_url, service_data)
        self.assertRedirects(
            response,
            reverse("catalog:service_list", args=[self.activity.slug]),
        )
        service = Service.objects.get(name="Coupe & coiffure")
        self.assertEqual(service.slug, "coupe-coiffure")
        self.assertEqual(service.price, Decimal("2500"))
        self.assertTrue(service.is_active)

        response = self.client.post(create_url, service_data)
        self.assertRedirects(
            response,
            reverse("catalog:service_list", args=[self.activity.slug]),
        )
        self.assertTrue(
            Service.objects.filter(name="Coupe & coiffure", slug="coupe-coiffure-2").exists()
        )

    def test_edit_service_saves_without_exposing_or_changing_slug(self):
        service = Service.objects.create(
            activity=self.activity,
            name="Coupe classique",
            slug="coupe-classique",
            price=Decimal("5000.00"),
            duration_minutes=45,
            description="Ancienne description",
        )
        edit_url = reverse(
            "catalog:service_edit",
            kwargs={"activity_slug": self.activity.slug, "slug": service.slug},
        )

        get_response = self.client.get(edit_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, 'name="is_active"')
        self.assertNotContains(get_response, 'name="slug"')

        response = self.client.post(
            edit_url,
            {
                "name": "Coupe classique premium",
                "description": "Nouvelle description",
                "price": "6500.00",
                "duration_minutes": "60",
                "is_active": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("catalog:service_list", args=[self.activity.slug]),
        )
        service.refresh_from_db()
        self.assertEqual(service.name, "Coupe classique premium")
        self.assertEqual(service.slug, "coupe-classique")
        self.assertEqual(service.description, "Nouvelle description")
        self.assertEqual(service.price, Decimal("6500.00"))
        self.assertEqual(service.duration_minutes, 60)
        self.assertTrue(service.is_active)
        self.assertEqual(
            list(PriceHistory.objects.filter(object_id=service.pk).values_list("price", flat=True)),
            [Decimal("6500.00"), Decimal("5000.00")],
        )