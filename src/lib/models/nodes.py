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

    paperID: str
    url: str
    title: str
    isOpenAccess: bool
    abstract: Optional[str]
    year: Optional[int]
    openAccessPDFUrl: Optional[str]
    publicationTypes: Optional[List[str]]
    embedding: Optional[_Embedding]
    tldr: Optional[_Tdlr]


class FieldOfStudy(BaseModel):
    "A field of study, e.g. Machine Learning, Computer Vision, etc."

    name: str


class Proceedings(BaseModel):
    "A conference or workshop proceedings"

    proceedingsID: str
    year: int


class JournalVolume(BaseModel):
    "A volume of a journal"

    journalVolumeID: str
    volume: Optional[int]


class OtherPublicationVenue(BaseModel):
    venueID: str
    name: str
    url: Optional[str]
    alternateNames: List[str]


class Journal(BaseModel):
    "A journal"

    journalID: str
    name: str
    url: Optional[str]
    alternateNames: List[str]


class Workshop(BaseModel):
    "A workshop venue"

    workshopID: str
    name: str
    url: Optional[str]
    alternateNames: List[str]


class Conference(BaseModel):
    "A conference venue"

    conferenceID: str
    name: str
    url: Optional[str]
    alternateNames: List[str]


class City(BaseModel):
    "A city"

    name: str


class Author(BaseModel):
    "An author of one or many publications"

    authorID: str
    url: str
    name: str
    homepage: Optional[str]
    hIndex: Optional[int]


class Organization(BaseModel):
    "An organization, e.g. a university, a company, etc. to which one or more authors are affiliated"

    name: str
