from django.db import migrations


def remove_exact_duplicates(apps, schema_editor):
    PriceHistory = apps.get_model("catalog", "PriceHistory")
    database = schema_editor.connection.alias
    rows = PriceHistory.objects.using(database).order_by(
        "content_type_id",
        "object_id",
        "price",
        "starts_at",
        "ends_at",
        "created_by_id",
        "id",
    )

    previous_key = None
    duplicate_ids = []
    for row in rows.iterator():
        key = (
            row.content_type_id,
            row.object_id,
            row.price,
            row.starts_at,
            row.ends_at,
            row.created_by_id,
        )
        if key == previous_key:
            duplicate_ids.append(row.pk)
        else:
            previous_key = key

    for start in range(0, len(duplicate_ids), 500):
        PriceHistory.objects.using(database).filter(
            pk__in=duplicate_ids[start : start + 500]
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_product_average_cost_product_stock_quantity"),
    ]

    operations = [
        migrations.RunPython(remove_exact_duplicates, migrations.RunPython.noop),
    ]