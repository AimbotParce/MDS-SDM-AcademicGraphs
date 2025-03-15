from typing import List

from pydantic import BaseModel

###########################################
# MODELS FOR THE ACADEMIC KNOWLEDGE GRAPH #
#                                         #
# Node models                             #
###########################################


class Publication(BaseModel):
    "A publication in the academic world"

    url: str
    title: str
    abstract: str
    year: int
    isOpenAccess: bool
    openAccessPDFUrl: str
    publicationType: str
    embedding: List[float]
    tldr: str


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
    hIndex: int


class Organization(BaseModel):
    "An organization, e.g. a university, a company, etc. to which one or more authors are affiliated"

    name: str
