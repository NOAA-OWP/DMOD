from django.contrib import admin

from . import models


class InlineFormulationParameterAdmin(admin.TabularInline):
    model = models.FormulationParameter
    extra = 1


class FormulationAdmin(admin.ModelAdmin):
    model = models.Formulation
    inlines = [InlineFormulationParameterAdmin]


# Register your models here.
admin.site.register(models.Formulation, FormulationAdmin)
