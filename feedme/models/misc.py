from typing import Dict, List, Optional, Tuple

from pydantic import Field, PositiveFloat, PositiveInt

from feedme.models.base import dataclass


@dataclass
class MinMaxInt:
    min: PositiveInt
    max: PositiveInt


@dataclass
class MinMaxFloat:
    min: PositiveFloat
    max: PositiveFloat


@dataclass
class OnnxData:
    filter: str
    remove: str
    retries: PositiveInt
    poll: PositiveInt


@dataclass
class SingleLlmData:
    model: str
    temperature: float


@dataclass
class LlmData:
    gpt2: str
    creative: SingleLlmData
    manager: SingleLlmData


@dataclass
class BotData:
    name: str
    # TODO: url


@dataclass
class CfgData(MinMaxFloat):
    increment: PositiveFloat


@dataclass
class StepData(MinMaxInt):
    increment: PositiveInt


@dataclass
class ImageData:
    batch: PositiveInt
    cfg: CfgData
    count: MinMaxInt
    steps: StepData
    extra: int = Field(default=0)


@dataclass
class InterestData(MinMaxInt):
    pass


@dataclass
class PostData:
    count: int
    retry: int


@dataclass
class ConceptRankingData:
    max: PositiveInt
    threshold: PositiveFloat


@dataclass
class ImageRankingData:
    max: PositiveInt
    threshold: PositiveFloat


@dataclass
class PostRankingData:
    threshold: PositiveFloat


@dataclass
class RankingData:
    concept: ConceptRankingData
    image: ImageRankingData
    post: PostRankingData


@dataclass
class MiscData:
    formats: List[str]
    modifiers: Dict[str, str]
    checkpoints: List[str]
    onnx: Optional[OnnxData]
    llms: LlmData
    sizes: Dict[str, Tuple[PositiveInt, PositiveInt]]
    bot: BotData
    images: ImageData
    interests: InterestData
    posts: PostData
    ranking: RankingData
