# Generated by Django 3.1.1 on 2020-09-11 09:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parser', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='file_csv',
            field=models.FileField(blank=True, null=True, upload_to='csv'),
        ),
    ]
