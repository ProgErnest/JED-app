# Données initiales : activités métier du projet JED (JED-02).

from django.db import migrations


ACTIVITES = [
    ("Restaurant-bar", "restaurant-bar", "Vente sur place et à emporter — plats, boissons, service bar."),
    ("Coiffure", "coiffure", "Prestations de coiffure et vente de produits associés."),
    ("Boutique", "boutique", "Vente au détail de produits en stock."),
]


def create_initial_activities(apps, schema_editor):
    Activity = apps.get_model("activities", "Activity")
    for name, slug, description in ACTIVITES:
        Activity.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "description": description, "is_active": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_initial_activities, migrations.RunPython.noop),
    ]
