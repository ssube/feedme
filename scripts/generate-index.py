from datetime import datetime
from json import load
from os import listdir, path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from feedme.data import get_bot_name

DEFAULT_TEMPLATE = "index.html.j2"


def list_posts(root: str):
    children = listdir(root)
    folders = [f for f in children if path.isdir(path.join(root, f))]

    # sort by modification time
    folders.sort(key=lambda f: path.getmtime(path.join(root, f)), reverse=True)

    posts = []
    for folder in folders:
        post_file = path.join(root, folder, "post.json")
        if not path.isfile(post_file):
            continue

        with open(post_file, "r") as f:
            post_data = load(f)

        mtime = path.getmtime(path.join(root, folder))
        timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

        title = post_data.get("title", folder)
        images = listdir(path.join(root, folder))
        images = [
            f
            for f in images
            if path.isfile(path.join(root, folder, f)) and f.endswith(".png")
        ]
        post = {
            "folder": folder,
            "title": title,
            "images": images,
            "timestamp": timestamp,
        }
        posts.append(post)

    return posts


def template_page(title, posts, template=None):
    if template is None:
        template = DEFAULT_TEMPLATE

    env = Environment(
        loader=FileSystemLoader("feedme/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template)
    result = template.render(title=title, posts=posts)

    with open("index.html", "w") as f:
        f.write(result)

    return result


def main():
    posts = list_posts("/tmp/feedme/approved")
    template_page("FeedMe", posts)


if __name__ == "__main__":
    main()
