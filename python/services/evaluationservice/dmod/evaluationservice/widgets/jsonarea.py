"""
Widgets for editing JSON
"""
from __future__ import annotations

import typing
import json

from pydantic import BaseModel
from pydantic import Field

from django.forms.widgets import Widget
from django.templatetags.static import static

_MODE = typing.Literal["code", "tree", "view", "preview"]
_SCHEMA = typing.Mapping[str, typing.Union[str, bool, int, typing.Sequence, typing.Mapping]]

class ExtraHandler(BaseModel):
    """
    DTO used to define how to extra scripts should be put into the template and how to attach handlers
    """
    script_path: str
    element_selector: str
    event: str
    function: str
    is_module: typing.Optional[bool] = Field(default=False)

class JSONArea(Widget):
    """
    A widget that provides advanced handling for JSON data and the application of schemas
    """
    class Media:
        # Add the raw editor and specialized functionality
        js = (
            "jsoneditor/jsoneditor.min.js",
            "js/widgets/jsonarea.js"
        )

        # Add required styling for the editor and additional styling overrides
        css = {
            'all': (
                'jsoneditor/jsoneditor.min.css',
                'css/widgets/jsonarea.css'
            )
        }

    template_name = "widgets/jsonarea.html"

    def __init__(
        self,
        attrs: dict = None,
        namespace: typing.Union[str, typing.Sequence[str]] = None,
        initial_mode: _MODE = None,
        available_modes: typing.List[_MODE] = None,
        schema: _SCHEMA = None,
        width: typing.Union[str, int, float] = None,
        height: typing.Union[str, int, float] = None,
        handlers: typing.List[ExtraHandler] = None,
        extra_data: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        """
        Constructor

        Args:
            attrs: A custom set of attributes to add to the core HTMLElement
            namespace: The namespace that should contain out-of-context access to the editor and accompanying data
            initial_mode: The starting editing mode
            available_modes: The modes that may be toggled on
            width: The desired width of the editor on the screen
            height: The desired height of the editor on the screen
            handlers: Additional handlers to attach at runtime
            extra_data: Additional, json serializable data to make accessible by the editor
            kwargs: Additional values to add as attributes
        """
        modes = available_modes or ['tree', 'code', 'view']
        default_options = {
            'modes': modes,
            'mode': initial_mode or "view" if 'view' in modes else modes[0],
            "schema": schema,
            "indentation": 4
        }

        if kwargs:
            default_options.update(kwargs)

        self.options = default_options
        self.width = width
        self.height = height
        self.namespace = [namespace] if isinstance(namespace, str) else namespace or ['editors']
        self.handlers = handlers or list()
        self.extra_data = extra_data or dict()

        super().__init__(attrs=attrs)

    def get_context(self, name, value, attrs) -> typing.Dict[str, typing.Any]:
        """
        Get additional values that should be passed to the renderer

        Args:
            name: The name of the field
            value: The value of the field
            attrs: Additional values that will be placed on the core htmlelement

        Returns:
            A dictionary containing everything needed to render the widget
        """
        context = super().get_context(name, value, attrs)

        context['widget']['options'] = json.dumps(self.options)
        context['widget']['width'] = self.width
        context['widget']['height'] = self.height
        context['widget']['namespace'] = self.namespace
        context['widget']['handlers'] = self.handlers

        # Create a list of unique combinations of script paths and if they are modules to be imported.
        # This ensures that these script elements will only be created once.
        context['widget']['extra_scripts'] = list({
            (static(handler.script_path), handler.is_module)
            for handler in self.handlers
            if handler.script_path
        })

        # Extra Data needs to be delimited by the name of the widget. It's unlikely, but if there is another one of
        # these editors on the screen, this will help prevent data conflicts
        context['widget']['extra_data'] = {
            f"{name}-{key}": value
            for key, value in self.extra_data.items()
        }

        return context