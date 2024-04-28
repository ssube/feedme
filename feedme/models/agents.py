from typing import Dict, List, Optional, Union

from pydantic import BaseModel


class InterestModel(BaseModel):
    backstory: Union[str, List[str]]
    category: Optional[str]


class AgentsModel(BaseModel):
    backstory: Dict[str, str]
    interests: Dict[str, Union[str, InterestModel]]
