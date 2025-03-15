from typing import List, Optional

from pydantic import BaseModel

###########################################
# MODELS FOR THE ACADEMIC KNOWLEDGE GRAPH #
#                                         #
# Edge models                             #
###########################################


class Cites(BaseModel):
    "(Citation) -[Cites]-> (Publication)"

    isInfluential: bool
    contexts: List[str]
    intents: List[str]


class HasFieldOfStudy(BaseModel):
    "(Publication) -[HasFieldOfStudy]-> (FieldOfStudy)"


class Wrote(BaseModel):
    "(Author) -[Wrote]-> (Publication)"


class MainAuthor(BaseModel):
    "(Publication) -[MainAuthor]-> (Author)"


class IsAffiliatedWith(BaseModel):
    "(Author) -[IsAffiliatedWith]-> (Organization)"


class Reviewed(BaseModel):
    "(Author) -[Reviewed]-> (Publication)"

    accepted: bool
    minorRevisions: int
    majorRevisions: int
    reviewContent: str


class IsPublishedIn(BaseModel):
    "(Publication) -[PublishedIn]-> (JournalVolume|Proceedings)"

    pageNumberRange: Optional[str]


class IsEditionOf(BaseModel):
    """
    (JournalVolume) -[IsEditionOf]-> (Journal)
    or
    (Proceedings) -[IsEditionOf]-> (Conference|Workshop)
    """


class IsHeldIn(BaseModel):
    "(Proceedings) -[IsHeldIn]-> (City)"
