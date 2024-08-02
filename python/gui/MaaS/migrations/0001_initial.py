# A migration to apply an initial superuser

import os
from django.db import migrations


class Migration(migrations.Migration):
    initial=True
    dependencies = [ ('auth', '__latest__') ]
    def create_superuser(apps, schema_editor):
        from django.contrib.auth.models import User

        SU_NAME = os.environ.get('DMOD_SU_NAME', "dmod_admin")
        SU_EMAIL = os.environ.get('DMOD_SU_EMAIL', "dmod_admin@noaa.gov")
        SU_PASSWORD = os.environ.get('DMOD_SU_PASSWORD', f"{SU_NAME}{os.environ.get('SQL_PASSWORD')}")

        superuser = User.objects.create_superuser(
            username=SU_NAME,
            email=SU_EMAIL,
            password=SU_PASSWORD)

        superuser.save()

    operations = [
        migrations.RunPython(create_superuser),
    ]
