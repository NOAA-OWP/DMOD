# Generated by Django 3.2.15 on 2022-08-15 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EvaluationDefinition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The name of the evaluation', max_length=255)),
                ('author', models.CharField(blank=True, help_text='The name of the author of the evaluation', max_length=255, null=True)),
                ('description', models.TextField(blank=True, help_text='A helpful description of what the evaluation is intended to do', null=True)),
                ('definition', models.JSONField(help_text='The raw json that will be sent as the instructions to the evaluation service')),
                ('last_edited', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('name', 'author', 'description')},
            },
        ),
    ]
