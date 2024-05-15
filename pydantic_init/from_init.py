import inspect
import json
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Generator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from docstring_parser import parse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    TypeAdapter,
    alias_generators,
    create_model,
)
from pydantic_core.core_schema import (
    CoreSchema,
    SerSchema,
    no_info_after_validator_function,
    union_schema,
)
from typing_extensions import Annotated, Self

T = TypeVar('T')
B = TypeVar('B', bound=BaseModel)
PathOrStr = Union[Path, str]


def create_method_model(method: Callable[..., Any], model_name: str) -> Type[BaseModel]:
    signature = inspect.signature(method)
    params_desctiption = {}
    if method.__doc__:
        docstring = parse(method.__doc__)
        method_description = docstring.short_description
        for param in docstring.params:
            params_desctiption[param.arg_name] = param.description
    else:
        method_description = None

    fields = {}
    if method.__name__ != '__init__':
        fields['from_method'] = (str, method.__name__)
    for name, param in signature.parameters.items():
        if name == 'self':
            continue
        default = param.default
        if default is inspect._empty:
            field = (
                Annotated[param.annotation, Field(description=params_desctiption.get(name))],
                Field(...),
            )
        else:
            field = (
                Annotated[param.annotation, Field(description=params_desctiption.get(name))],
                default,
            )
        fields[name] = field
    return create_model(
        model_name,
        **fields,
        __doc__=method_description,
        __config__=ConfigDict(protected_namespaces=()),
    )


class FromInitMixin:
    __from_methods: ClassVar[Union[List[str], str]] = '*'

    @classmethod
    def ser_schema(cls) -> Optional[SerSchema]:
        return None

    @classmethod
    def model_validate(cls, object_: Any, **kwargs: Any) -> Self:
        return TypeAdapter(cls).validate_python(object_, **kwargs)

    @classmethod
    def _from_init_dicts(cls, model: BaseModel) -> Self:
        kwargs = model.model_dump()
        from_method = kwargs.pop('from_method', None)
        if from_method is None:
            if issubclass(cls, BaseModel):
                return cls.model_construct(**kwargs)
            return cls(**kwargs)
        return getattr(cls, from_method)(**kwargs)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Type[Any], handler: GetCoreSchemaHandler) -> CoreSchema:
        schemas = [
            create_method_model(
                method=from_method,
                model_name=cls._generate_from_model_name(from_method.__name__),
            )
            for from_method in cls._find_all_from_methods()
        ]
        choices: list[CoreSchema] = [TypeAdapter(schema).core_schema for schema in schemas]
        if issubclass(cls, BaseModel):
            choices.append(handler(source))
        else:
            choices.append(
                TypeAdapter(
                    create_method_model(
                        method=cls.__init__,
                        model_name=cls._generate_from_model_name('init'),
                    )
                ).core_schema
            )
        return no_info_after_validator_function(
            cls._from_init_dicts,
            union_schema(choices=choices),  # type: ignore
            serialization=cls.ser_schema(),
        )

    @classmethod
    def _generate_from_model_name(cls, from_method_name: str) -> str:
        return alias_generators.to_pascal(cls.__name__) + alias_generators.to_pascal(from_method_name)

    @classmethod
    def _find_all_from_methods(cls) -> Generator[Callable[..., Any], None, None]:
        if cls.__from_methods == '*':
            for k in cls.__dict__:
                if k.startswith('from_'):
                    yield getattr(cls, k)
        else:
            for k in cls.__from_methods:
                yield getattr(cls, k)


def save_json_schema(model: Union[TypeAdapter[T], Type[BaseModel]], output_file: PathOrStr) -> None:
    output_file = Path(output_file)
    json_schema = model.json_schema() if isinstance(model, TypeAdapter) else model.model_json_schema()
    output_file.write_text(json.dumps(json_schema, indent=2))


def create_json_with_schema(model: Union[TypeAdapter[T], Type[BaseModel]], output_file: PathOrStr) -> None:
    output_file = Path(output_file)
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    schema_file = output_file.with_suffix('.schema.json')
    save_json_schema(model, output_file.with_suffix('.schema.json'))
    data = {
        '$schema': str(schema_file.resolve()),
    }
    output_file.write_text(json.dumps(data, indent=2))
