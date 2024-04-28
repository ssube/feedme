from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel


class OnnxData(BaseModel):
    filter: str
    remove: str
    retries: int
    poll: int
    batch: int  # TODO: move to ImageData
    extra: int  # TODO: move to ImageData


class LlmData(BaseModel):  # TODO: add a nested model for each llm
    gpt2: str
    creative: str
    creative_temperature: float
    manager: str
    manager_temperature: float


class BotData(BaseModel):
    name: str
    # TODO: url


class ImageData(BaseModel):
    min: int
    max: int
    batch: int
    extra: int


class InterestData(BaseModel):
    min: int
    max: int


class PostData(BaseModel):
    count: int
    retry: int


class ConceptRankingData(BaseModel):
    max: int
    threshold: float


class ImageRankingData(BaseModel):
    max: int
    threshold: float


class PostRankingData(BaseModel):
    threshold: float


class RankingData(BaseModel):
    concept: ConceptRankingData
    image: ImageRankingData
    post: PostRankingData


class MiscData(BaseModel):
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
