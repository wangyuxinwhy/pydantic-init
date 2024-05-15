from importlib import import_module
from types import ModuleType
from typing import Any, Dict

from pydantic import BaseModel

from pydantic_init.from_init import FromInitMixin


def init(node: Dict[str, Any], *args: Any, **kwargs: Any) -> Any:
    if (component_path := node.get('_component_')) is None:
        raise ValueError('No _component_ key found in node')

    component_cls = _get_component_from_path(component_path)
    args = tuple(node.get('_args_', ())) + args
    kwargs = {**{k: v for k, v in node.items() if k not in ('_component_', '_args_')}, **kwargs}
    try:
        should_validate = issubclass(component_cls, (BaseModel, FromInitMixin))
    except TypeError:
        should_validate = False
    if should_validate:
        if args:
            raise ValueError('Args are not supported for pydantic models or FromInitMixin components.')
        return component_cls.model_validate(kwargs)
    return component_cls(*args, **kwargs)


def _get_component_from_path(path: str) -> Any:
    if path == '':
        raise ValueError('Empty path')

    parts = list(path.split('.'))
    for part in parts:
        # If a relative path is passed in, the first part will be empty
        if not len(part):
            raise ValueError(f"Error loading '{path}': invalid dotstring." + '\nRelative imports are not supported.')
    # First module requires trying to import to validate
    part0 = parts[0]
    try:
        obj = import_module(part0)
    except ImportError as exc_import:
        raise ValueError(
            f"Error loading '{path}':\n{repr(exc_import)}" + f"\nAre you sure that module '{part0}' is installed?"
        ) from exc_import
    # Subsequent components can be checked via getattr() on first module
    # It can either be an attribute that we can return or a submodule that we
    # can import and continue searching
    for m in range(1, len(parts)):
        part = parts[m]
        try:
            obj = getattr(obj, part)
        # If getattr fails, check to see if it's a module we can import and
        # continue down the path
        except AttributeError as exc_attr:
            parent_dotpath = '.'.join(parts[:m])
            if isinstance(obj, ModuleType):
                mod = '.'.join(parts[: m + 1])
                try:
                    obj = import_module(mod)
                    continue
                except ModuleNotFoundError as exc_import:
                    raise ValueError(
                        f"Error loading '{path}':\n{repr(exc_import)}"
                        + f"\nAre you sure that '{part}' is importable from module '{parent_dotpath}'?"
                    ) from exc_import
                except Exception as exc_import:
                    raise ValueError(f"Error loading '{path}':\n{repr(exc_import)}") from exc_import
            # If the component is not an attribute nor a module, it doesn't exist
            raise ValueError(
                f"Error loading '{path}':\n{repr(exc_attr)}"
                + f"\nAre you sure that '{part}' is an attribute of '{parent_dotpath}'?"
            ) from exc_attr
    return obj
