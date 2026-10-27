from django.test import TestCase

from apps.activities.models import Activity


class InitialActivitiesTests(TestCase):
    def test_seed_migration_creates_the_three_business_activities(self):
        activities = set(Activity.objects.values_list("slug", flat=True))

        self.assertTrue(
            {"restaurant-bar", "coiffure", "boutique"}.issubset(activities)
        )
