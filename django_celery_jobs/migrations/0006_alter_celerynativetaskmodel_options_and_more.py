# Generated by Django 4.1.7 on 2023-05-04 13:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_celery_jobs', '0005_celerynativetaskmodel'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='celerynativetaskmodel',
            options={'ordering': ['-id']},
        ),
        migrations.AlterModelTable(
            name='celerynativetaskmodel',
            table='django_celery_jobs_native_jobs',
        ),
    ]
