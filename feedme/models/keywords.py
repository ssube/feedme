from typing import List

from pydantic import BaseModel


class KeywordsModel(BaseModel):
    quality: List[str]
    remove: List[str]
