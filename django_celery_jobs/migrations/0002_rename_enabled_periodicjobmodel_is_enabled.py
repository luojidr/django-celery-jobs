# Generated by Django 4.1.7 on 2023-04-06 17:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_celery_jobs', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='periodicjobmodel',
            old_name='enabled',
            new_name='is_enabled',
        ),
    ]