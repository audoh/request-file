import json
from enum import Enum
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import urlencode

from pydantic import BaseModel, Field, validator
from requests.models import CaseInsensitiveDict as _CaseInsensitiveDict


def _parse_bool(val: str) -> bool:
    if val.lower() in ("true", "1"):
        return True
    elif val.lower() in ("false", "0"):
        return False
    raise ValueError(f"invalid boolean value: {val}")


class Replacement(BaseModel):
    types: ClassVar[Dict[str, Callable[[str], Any]]] = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": _parse_bool,
    }

    name: str = Field(
        ...,
        description="The name of this replacement, which will be used to find it in the input or environment variables; defaults to the replacement string",
    )
    required: bool = True
    default: Optional[Any] = None
    type: str = Field("string", examples=[_type for _type in types])

    @property
    def has_default(self) -> bool:
        return "default" in self.__fields_set__

    def parse_value(self, value: str) -> Any:
        try:
            return self.types[self.type](value)
        except KeyError as exc:
            raise ValueError(f"unknown type {self.type}") from exc


# Unlike the one in requests, this one can be JSON serialised
T = TypeVar("T")


class CaseInsensitiveDict(Generic[T], Dict[str, T], _CaseInsensitiveDict[T]):
    pass


class RequestFile(BaseModel):
    replacements: Dict[str, Replacement] = Field(
        {},
        description="Describes the dynamic replacements available/required for this request",
    )
    url: str = Field(
        ...,
        description="Where to send the request, including any query string and anchor.",
        examples=["https://myapi.net/api/v1/cat/:name?query={{QUERY}}#{{ANCHOR}}"],
    )
    method: str = Field(
        "GET",
        description="The request method; can also be a replacement placeholder.",
        examples=["GET", "POST", "{{METHOD}}"],
    )
    headers: Dict[str, str] = Field(
        {},
        description="The headers to send for this request. Note that additional auto-generated headers, such as Content-Length and Content-Type, may also be sent.",
    )
    params: Dict[str, Union[str, List[str]]] = Field(
        {},
        description="Query/search parameters for this request. Lists of values are passed as repeated parameters i.e. param=1&param=2.",
    )
    body_text: Optional[str] = Field(
        None, alias="text", description="The raw body of this request, if applicable."
    )
    body_data: Optional[Dict[str, Any]] = Field(
        None, alias="data", description="The form data of this request, if applicable."
    )
    body_json: Any = Field(
        None, alias="json", description="The JSON data of this request, if applicable."
    )

    exports: Dict[str, str] = Field(
        {}, description="Path specs for variables to export from the response."
    )

    @validator("replacements", pre=True)
    @classmethod
    def prepare_replacements(cls: Type["RequestFile"], replacements: Any) -> Any:
        if isinstance(replacements, MutableMapping):
            for key, replacement in replacements.items():
                if not isinstance(replacement, MutableMapping):
                    continue
                if not replacement.get("name"):
                    replacement["name"] = key
        return replacements

    @validator("headers")
    @classmethod
    def convert_headers(
        cls: Type["RequestFile"], headers: Dict[str, str]
    ) -> CaseInsensitiveDict[str]:
        return CaseInsensitiveDict(headers)

    @classmethod
    def load(cls: Type["RequestFile"], path: str) -> "RequestFile":
        with open(path, "r") as fp:
            return cls(**json.load(fp))

    @staticmethod
    def _str(val: Any) -> str:
        if val == None:
            return "null"
        elif isinstance(val, bool):
            if val == True:
                return "true"
            else:
                return "false"
        elif isinstance(val, (int, float, str)):
            return str(val)
        raise ValueError(f"unsupported type {type(val)}")

    @staticmethod
    def _replace(val_in: Any, *, old: str, new: Any) -> Any:
        if isinstance(val_in, str):
            if val_in == old:
                return new
            else:
                return val_in.replace(old, RequestFile._str(new))
        elif isinstance(val_in, Mapping):
            val_out: Dict[str, Any] = {}
            for old_key, old_value in val_in.items():
                new_key = (
                    old_key.replace(old, RequestFile._str(new))
                    if isinstance(old_key, str)
                    else old_key
                )
                new_value = RequestFile._replace(old_value, old=old, new=new)
                val_out[new_key] = new_value
            return val_out
        elif isinstance(val_in, Iterable):
            return [
                RequestFile._replace(old_value, old=old, new=new)
                for old_value in val_in
            ]
        return val_in

    def replace(self, old: str, new: Any) -> "RequestFile":
        url = self.url.replace(old, RequestFile._str(new))
        method = RequestFile._str(new) if self.method == old else self.method
        headers = RequestFile._replace(self.headers, old=old, new=new)
        params = RequestFile._replace(self.params, old=old, new=new)
        text = RequestFile._replace(self.body_text, old=old, new=new)
        form_data = RequestFile._replace(self.body_data, old=old, new=new)
        json = RequestFile._replace(self.body_json, old=old, new=new)
        return self.copy(
            update={
                "url": url,
                "method": method,
                "headers": headers,
                "params": params,
                "body_text": text,
                "body_data": form_data,
                "body_json": json,
            }
        )

    @property
    def body(self) -> str:
        if self.body_text is not None:
            return self.body_text
        if self.body_data is not None:
            return urlencode(self.body_data)
        if self.body_json is not None:
            return json.dumps(self.body_json)
        return ""

    class Config:
        arbitrary_types_allowed: bool = True

        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Type["Replacement"]) -> None:
            schema["examples"] = [
                RequestFile(
                    replacements={":name": Replacement(required=True, name="CAT_NAME")},
                    url="https://myapi.net/api/v1/cats/:name",
                    method="POST",
                    headers={"Content-Type": "application/json"},
                    body={"petTheCat": True},
                )
            ]
