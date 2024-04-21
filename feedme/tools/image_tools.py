from json import dumps, loads
from os import listdir, path
from re import sub
from typing import Dict, List

from PIL import Image

from feedme.data import get_save_path


def image_size(filename: str) -> tuple[int, int]:
    """
    Get the size of an image file.
    """
    image_path = path.join(get_save_path(), filename)

    if path.exists(image_path):
        with Image.open(image_path) as img:
            return img.size

    raise FileNotFoundError(f"Image file {filename} not found")


def image_histogram(filename: str) -> List[int]:
    """
    Get the histogram of an image file.
    """
    return [0] * 256


def list_image_files() -> List[str]:
    """
    List all image files in the current directory. Listing images is expensive, so this tool should be used sparingly.
    """
    return [
        f
        for f in listdir(get_save_path())
        if path.isfile(path.join(get_save_path(), f)) and f.endswith(".png")
    ]


def get_image_data(root_path=get_save_path()) -> List[Dict[str, str]]:
    """
    Get the caption and size of all image files in the current directory.
    """
    images = []
    for f in listdir(root_path):
        if path.isfile(path.join(root_path, f)) and f.endswith(".png"):
            image_path = path.join(root_path, f)
            with Image.open(image_path) as img:
                images.append(
                    {
                        "filename": f,
                        "size": img.size,
                        "caption": read_prompt_file(f + ".json", root_path=root_path),
                    }
                )

    return dumps(images)


def read_prompt_file(filename: str, root_path=get_save_path()) -> str:
    with open(path.join(root_path, filename), "r") as f:
        prompt_data = loads(f.read())
        prompt = prompt_data.get("params", {}).get("prompt", "")
        prompt = prompt.split("||")[0]  # only use the first part, the detail prompt
        prompt = sub(r"<[^>]+>", "", prompt)  # remove any LoRA tokens
        return prompt[:200].strip()


def get_image_caption(filename: str) -> str:
    """
    Get the caption for a single image file.
    """
    caption_file = path.join(get_save_path(), filename + ".json")

    if path.exists(caption_file):
        return read_prompt_file(caption_file)

    raise FileNotFoundError(f"Caption file {filename} not found")


def list_image_captions() -> Dict[str, str]:
    """
    List all image captions in the current directory.
    """
    captions = {}
    for f in listdir(get_save_path()):
        if path.isfile(path.join(get_save_path(), f)) and f.endswith(".png"):
            caption_file = path.join(get_save_path(), f + ".json")
            if path.exists(caption_file):
                captions[f] = read_prompt_file(caption_file)

    return captions
