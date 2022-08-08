from typing import Union
from pydantic import BaseModel, Field


class Id(BaseModel):
    pkh: str
    sub: Union[str, None] = None


class Content(BaseModel):
    type: str
    data: str


class IPLDLink(BaseModel):
    link: str = Field(..., title="/", alias="/")


class PartialHead(BaseModel):
    id: Id
    content: Union[Content, None] = None
    ref: Union[IPLDLink, None] = None


class Head(PartialHead):
    sig: str
