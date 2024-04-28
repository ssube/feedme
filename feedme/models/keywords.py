from typing import List

from feedme.models.base import dataclass


@dataclass
class KeywordsModel:
    quality: List[str]
    remove: List[str]
