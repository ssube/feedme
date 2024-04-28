from typing import Dict, List, Optional, Union

from feedme.models.base import dataclass


@dataclass
class InterestModel:
    backstory: Union[str, List[str]]
    category: Optional[str]


@dataclass
class AgentsModel:
    backstory: Dict[str, str]
    interests: Dict[str, Union[str, InterestModel]]
