# Generated by Django 2.0.4 on 2019-03-11 14:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('golf_app', '0004_invite_number'),
    ]

    operations = [
        migrations.RenameField(
            model_name='invite',
            old_name='number',
            new_name='code',
        ),
    ]
