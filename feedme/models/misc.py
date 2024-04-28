from typing import Dict, List, Optional, Tuple

from feedme.models.base import dataclass


@dataclass
class MinMaxData:
    min: int
    max: int


@dataclass
class OnnxData:
    filter: str
    remove: str
    retries: int
    poll: int


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
class CfgData:
    increment: float
    min: float
    max: float


@dataclass
class StepData(MinMaxData):
    increment: int


@dataclass
class ImageData:
    batch: int
    cfg: CfgData
    count: MinMaxData
    extra: int
    steps: StepData


@dataclass
class InterestData(MinMaxData):
    pass


@dataclass
class PostData:
    count: int
    retry: int


@dataclass
class ConceptRankingData:
    max: int
    threshold: float


@dataclass
class ImageRankingData:
    max: int
    threshold: float


@dataclass
class PostRankingData:
    threshold: float


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
    sizes: Dict[str, Tuple[int, int]]
    bot: BotData
    images: ImageData
    interests: InterestData
    posts: PostData
    ranking: RankingData
