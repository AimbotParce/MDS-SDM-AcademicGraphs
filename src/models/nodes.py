from typing import List, Optional

from pydantic import BaseModel

###########################################
# MODELS FOR THE ACADEMIC KNOWLEDGE GRAPH #
#                                         #
# Node models                             #
###########################################


class Publication(BaseModel):
    "A publication in the academic world"

    class _Embedding(BaseModel):
        "The embedding of a publication"

        embedding: List[float]
        model: str

    class _Tdlr(BaseModel):
        "The TLDR of a publication"

        model: str
        text: str

    url: str
    title: str
    abstract: str
    year: int
    isOpenAccess: bool
    openAccessPDFUrl: Optional[str]
    publicationType: str
    embedding: Optional[_Embedding]
    tldr: Optional[_Tdlr]


class FieldOfStudy(BaseModel):
    "A field of study, e.g. Machine Learning, Computer Vision, etc."

    name: str


class Proceedings(BaseModel):
    "A conference or workshop proceedings"

    year: int


class JournalVolume(BaseModel):
    "A volume of a journal"

    year: int


class Journal(BaseModel):
    "A journal"

    name: str


class Workshop(BaseModel):
    "A workshop venue"

    name: str


class Conference(BaseModel):
    "A conference venue"

    name: str


class City(BaseModel):
    "A city"

    name: str


class Author(BaseModel):
    "An author of one or many publications"

    url: str
    name: str
    homepage: str
    hIndex: str


class Organization(BaseModel):
    "An organization, e.g. a university, a company, etc. to which one or more authors are affiliated"

    name: str
