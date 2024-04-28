from pydantic import BaseModel


class PromptsModel(BaseModel):
    choose_image_size: str
    critique_image_binary: str
    critique_image_opinion: str
    critique_image_scale: str
    demo_idea: str
    demo_post: str
    elaborate_characters: str
    elaborate_quality: str
    elaborate_scene: str
    generate_concepts: str
    generate_description: str
    generate_ideas: str
    generate_keywords: str
    generate_prompt: str
    negative_prompt: str
    post_notice: str
    rank_concepts_binary: str
    rank_concepts_scale: str
    rank_image_sort: str
    rank_image_sort_retry: str
    rank_image_binary: str
    rank_image_scale: str
    rank_image_scale_variable: str
    remove_concepts: str
