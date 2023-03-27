from django.contrib import admin
from django.http import HttpRequest

from . import models


class SpecificationTemplateAdmin(admin.ModelAdmin):
    """
    A dedicated view to edit a Specification class instance
    """

    fields = (
        "template_specification_type",
        "template_name",
        "template_description",
        "template_configuration"
    )

    # Display these fields on the list screen
    list_display = ('template_specification_type', 'template_name', 'template_description',)

    # Regardless of what fields are displayed on the screen,
    # we want to be able to enter the editor by clicking on the template_name
    list_display_links = ('template_name',)

    # Allow users to filter results by these fields
    list_filter = ("template_specification_type",)

    def get_list_display(self, request: HttpRequest) -> (str,):
        """
        Gets the fields that may be shown as columns on the list screen

        :param HttpRequest request: The request that asked for the columns
        :rtype: (str,)
        :return: The fields to display on the list screen
        """
        # Get the master list of columns to show
        list_display = super(SpecificationTemplateAdmin, self).get_list_display(request)

        # If the user is a superuser, they'll see DataSources belonging to all users;
        # tack the author's name to it so that superusers may know whose DataSources they are editing
        if request.user.is_superuser:
            list_display = ["author"] + list(list_display)

        return list_display

    def get_list_filter(self, request: HttpRequest) -> (str,):
        """
        Gets the list of fields that elements may be filtered by. This will show a box on the side of the
        screen where a user may click a link that might limit all elements displayed on the screen to those
        whose variables are 'flow'

        :param HttpRequest request: The request asking for which fields to allow a user to filter by
        :rtype: (str,)
        :return: A collection of all fields to filter by
        """
        list_filter = super(SpecificationTemplateAdmin, self).get_list_filter(request)

        # If the user is a superuser, they will also be able to see the authors of the datasources.
        # Allow the user to limit displayed items to those owned by specific users
        if request.user.is_superuser:
            list_filter = ["author"] + list(list_filter)

        return list_filter

    def get_readonly_fields(self, request: HttpRequest, obj: models.SpecificationTemplate = None) -> (str,):
        """
        Determines which fields should not be available for editing

        :param HttpRequest request: The request asking which fields displayed on the screen should be read only
        :param models.DataSource obj: The datasource whose fields may be displayed on the screen
        :rtype: (str,)
        :return: A collection of all fields that cannot be modified
        """
        readonly_fields = super(SpecificationTemplateAdmin, self).get_readonly_fields(request, obj)

        # If a user is a superuser, they will see the name of the author.
        # In order to prevent the user from changing that, we set it as read-only
        if request.user.is_superuser:
            readonly_fields = tuple(['author'] + list(readonly_fields))

        return readonly_fields

    def save_model(self, request, obj, form, change):
        """
        Attaches the user to the object and calls the parent save method

        :type request: HttpRequest
        :param request: The web request
        :type obj: DataSource
        :param obj: The object that is to be saved
        :param form: The form that called the save function
        :param change: The change to the object
        :return: The result of the parent class's save_model function
        """

        # If the object doesn't have an author, make the current user
        if obj.author_id is None:
            obj.author = request.user

        super(SpecificationTemplateAdmin, self).save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        """
        Gets the custom form used for validation for the data source being edited

        :param request: The request that asked for the form
        :param obj: The object to edit
        :param kwargs: Keyword arguments being passed down the line
        :return: The form that will be used to validate the values configured for the data source
        """

        # First perform what it would have done prior. It's complicated logic and we can't do better
        form = super().get_form(request, obj, **kwargs)

        if form and hasattr(form, "editor"):
            # All we want to do is attach the user, so we go ahead and do that now
            form.editor = request.user

        return form

    def get_queryset(self, request):
        """
        Obtains a set of the appropriate data source configurations to load into the list view

        :type request: HttpRequest
        :param request: The http request that told the application to load data source configurations into the list
        :rtype: QuerySet[DataSource]
        :return: A QuerySet containing all DataSource objects that may be edited.
        """
        qs = super(SpecificationTemplateAdmin, self).get_queryset(request)

        # If the user isn't a superuser, only the user's DataSource objects will be returned
        if not request.user.is_superuser:
            qs = qs.filter(author=request.user)

        return qs


# Register your models here.
admin.site.register(models.StoredDataset)
admin.site.register(models.EvaluationDefinition)
admin.site.register(models.SpecificationTemplate, SpecificationTemplateAdmin)