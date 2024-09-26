# Generated by Django 4.2.7 on 2024-08-06 09:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Error",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("subject", models.CharField(max_length=255)),
                ("level", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "ordering": ["-timestamp"],
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="Log",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default=None,
                        max_length=32,
                        null=True,
                    ),
                ),
                ("group", models.CharField(db_index=True, max_length=60)),
                ("code", models.CharField(db_index=True, max_length=60)),
                ("account_id", models.BigIntegerField(default=-1)),
                (
                    "account_code",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default=None,
                        max_length=32,
                        null=True,
                    ),
                ),
                (
                    "account_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "account_username",
                    models.CharField(blank=True, max_length=150, null=True),
                ),
                (
                    "account_email",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "account_image",
                    models.ImageField(blank=True, null=True, upload_to=""),
                ),
                ("content_id", models.IntegerField(default=-1)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                ("note", models.TextField(blank=True)),
                ("payload", models.TextField(blank=True, default="{}")),
                ("data_old", models.TextField(blank=True, default="{}")),
                ("data_new", models.TextField(blank=True, default="{}")),
                ("status", models.CharField(blank=True, max_length=120)),
                ("status_code", models.PositiveIntegerField(db_index=True)),
                (
                    "datetime_create",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("datetime_update", models.DateTimeField(auto_now=True)),
                (
                    "content_type",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "verbose_name": "log.log",
                "ordering": ["-datetime_create"],
                "default_permissions": ("add", "change", "delete", "view"),
            },
        ),
        migrations.CreateModel(
            name="ActionLog",
            fields=[
                (
                    "log_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="log.log",
                    ),
                ),
            ],
            bases=("log.log",),
        ),
        migrations.CreateModel(
            name="LogStore",
            fields=[
                (
                    "log_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="log.log",
                    ),
                ),
            ],
            bases=("log.log",),
        ),
        migrations.CreateModel(
            name="RequestLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("method", models.CharField(max_length=255)),
                ("path", models.CharField(max_length=255)),
                ("payload", models.TextField(blank=True, default="{}")),
                ("status_code", models.CharField(max_length=255)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "account",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Content",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("content_id", models.IntegerField(default=-1)),
                (
                    "group_code",
                    models.CharField(db_index=True, max_length=32, null=True),
                ),
                (
                    "action_code",
                    models.CharField(db_index=True, max_length=32, null=True),
                ),
                ("method", models.CharField(blank=True, max_length=32)),
                ("data", models.TextField(blank=True, null=True)),
                ("data_2", models.TextField(blank=True, null=True)),
                ("url", models.TextField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("payload", models.TextField(blank=True, default="{}")),
                ("response", models.TextField(blank=True, default="{}")),
                ("response_code", models.IntegerField(null=True)),
                (
                    "datetime_create",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                (
                    "account",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "ordering": ["-datetime_create"],
            },
        ),
    ]