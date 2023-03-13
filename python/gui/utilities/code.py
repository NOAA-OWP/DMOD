"""
Put a module wide description here
"""
import typing
import math
import json


class CodeView:
    def __init__(
        self,
        name: str,
        container: str,
        textarea: str,
        tab: str = None,
        config: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        self.name = name
        self.container = container
        self.textarea = textarea
        self.tab = tab
        self.config = {
            "indentUnit": 4,
            "lineNumbers": True,
            "viewportMargin": math.inf,
            "matchBrackets": True,
            "autoCloseBrackets": True,
            "foldGutter": True,
            "gutters": [
                "CodeMirror-linenumbers",
                "CodeMirror-foldgutter"
            ]
        }

        for key, value in kwargs.items():
            self.config[key] = value

        if config and isinstance(config, typing.Mapping):
            for key, value in config.items():
                self.config[key] = value

    def set(self, key: str, value) -> "CodeView":
        self.config[key] = value
        return self

    def in_json(self) -> "CodeView":
        self.config['mode'] = 'javascript'
        self.config['json'] = True
        return self

    def to_dict(self) -> dict:
        view = {
            "name": self.name,
            "tab": self.tab,
            "container": self.container,
            "config": self.config.copy(),
            "textarea": self.textarea if self.textarea.startswith("#") else f"#{self.textarea}"
        }
        return view


class CodeViews(typing.Sequence[CodeView]):
    def __getitem__(self, index: typing.Union[int, slice]) -> typing.Union[CodeView, typing.Sequence[CodeView]]:
        return self.__code_views[index]

    def __len__(self) -> int:
        return len(self.__code_views)

    def __iter__(self) -> typing.Iterator[CodeView]:
        return iter(self.__code_views)

    def __init__(self, *args):
        non_view_args = [
            arg for arg in args if not isinstance(arg, CodeView)
        ]

        if non_view_args:
            raise Exception(
                f"Cannot form CodeViews collection. "
                f"The collection can only hold CodeViews and {len(non_view_args)} out of {len(args)} arguments "
                f"are not CodeViews"
            )

        self.__code_views: typing.List[CodeView] = [arg for arg in args]

    def append(self, view: CodeView) -> "CodeViews":
        if not isinstance(view, CodeView):
            raise Exception(f"Cannot add {type(view)} to CodeView collection")

        self.__code_views.append(view)
        return self

    def extend(self, views: typing.Collection[CodeView]) -> "CodeViews":
        non_view_args = [
            view for view in views if not isinstance(view, CodeView)
        ]

        if non_view_args:
            raise Exception(
                f"Cannot add CodeViews to collection. "
                f"The collection can only hold CodeViews and {len(non_view_args)} out of {len(views)} arguments "
                f"are not CodeViews"
            )

        self.__code_views.extend(views)

        return self

    def clear(self) -> "CodeViews":
        self.__code_views.clear()
        return self

    def copy(self) -> "CodeViews":
        return self.__class__(*self.__code_views)

    def add(
        self,
        name: str,
        container: str,
        textarea: str,
        tab: str = None,
        config: typing.Dict[str, typing.Any] = None,
        **kwargs
    ) -> "CodeViews":
        view = CodeView(name=name, container=container, textarea=textarea, tab=tab, config=config, **kwargs)
        self.__code_views.append(view)
        return self

    def insert(self, index: int, view: CodeView) -> "CodeViews":
        if not isinstance(view, CodeView):
            raise Exception(
                f"Cannot add CodeView to collection. "
                f"Only CodeView objects may be added and the encountered value was a {type(view)}"
            )

        self.__code_views.insert(index, view)
        return self

    def pop(self, index: int) -> "CodeViews":
        self.__code_views.pop(index)
        return self

    def to_json(self):
        return json.dumps(
            [
                view.to_dict()
                for view in self.__code_views
            ],
            indent=4,
            allow_nan=True
        )
