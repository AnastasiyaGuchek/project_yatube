# Generated by Django 2.2.16 on 2023-01-09 21:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0006_comment'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={'ordering': ['-created']},
        ),
        migrations.RenameField(
            model_name='comment',
            old_name='pub_date',
            new_name='created',
        ),
    ]
