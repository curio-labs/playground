# Generated by Django 5.1.1 on 2024-09-16 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0004_promptresult"),
    ]

    operations = [
        migrations.AddField(
            model_name="promptresult",
            name="playground",
            field=models.CharField(default=None, max_length=255, null=True),
        ),
    ]
