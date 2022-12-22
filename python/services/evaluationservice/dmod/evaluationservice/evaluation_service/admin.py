from django.contrib import admin

from . import models


# Register your models here.
admin.site.register(models.StoredDataset)
admin.site.register(models.EvaluationDefinition)