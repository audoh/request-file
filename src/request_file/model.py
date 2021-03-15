import json
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence, Type
from urllib.parse import urlencode

from pydantic import BaseModel, Field, validator
from requests.models import CaseInsensitiveDict


class Replacement(BaseModel):
    name: str = Field(
        ...,
        description="The name of this replacement, which will be used to find it in the input or environment variables; defaults to the replacement string",
    )
    required: bool = True
    default: Optional[str] = None


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
    body_text: Optional[str] = Field(
        None, alias="text", description="The raw body of this request, if applicable."
    )
    body_data: Optional[Dict[str, Any]] = Field(
        None, alias="data", description="The form data of this request, if applicable."
    )
    body_json: Any = Field(
        None, alias="json", description="The JSON data of this request, if applicable."
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
    def _replace(val_in: Any, *, old: str, new: str) -> Any:
        if isinstance(val_in, Mapping):
            val_out: Dict[str, Any] = {}
            for old_key, old_value in val_in.items():
                new_key = old_key.replace(old, new)
                new_value = RequestFile._replace(old_value, old=old, new=new)
                val_out[new_key] = new_value
            return val_out
        elif isinstance(val_in, Sequence):
            return [
                RequestFile._replace(old_value, old=old, new=new)
                for old_value in val_in
            ]
        elif isinstance(val_in, str):
            return val_in.replace(old, new)
        return val_in

    def replace(self, old: str, new: str) -> "RequestFile":
        url = self.url.replace(old, new)
        method = new if self.method == old else self.method
        headers = RequestFile._replace(self.headers, old=old, new=new)
        text = RequestFile._replace(self.body_text, old=old, new=new)
        form_data = RequestFile._replace(self.body_data, old=old, new=new)
        json = RequestFile._replace(self.body_json, old=old, new=new)
        return self.copy(
            update={
                "url": url,
                "method": method,
                "headers": headers,
                "text": text,
                "form_data": form_data,
                "json": json,
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
                ).dict()
            ]
