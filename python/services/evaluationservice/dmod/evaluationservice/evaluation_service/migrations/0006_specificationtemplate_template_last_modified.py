# Generated by Django 4.2.5 on 2023-10-30 20:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation_service', '0005_remove_specificationtemplate_unique_template_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='specificationtemplate',
            name='template_last_modified',
            field=models.DateTimeField(auto_now=True, help_text='When this was last modified'),
        ),
    ]