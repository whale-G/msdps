# Generated by Django 5.1.6 on 2025-06-03 04:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gc_dt", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gc_userfiles",
            name="process_id",
            field=models.CharField(max_length=256, primary_key=True, serialize=False),
        ),
    ]
