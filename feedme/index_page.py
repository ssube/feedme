from datetime import datetime
from json import load
from logging import getLogger
from os import environ, listdir, path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from feedme.data import misc

logger = getLogger(__name__)

DEFAULT_TEMPLATE = "index.html.j2"


def list_posts(root: str):
    logger.debug(f"Listing posts in {root}")
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


def template_page(title, posts, template=None, **kwargs):
    if template is None:
        template = DEFAULT_TEMPLATE

    env = Environment(
        loader=FileSystemLoader("feedme/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template)
    result = template.render(title=title, posts=posts, **kwargs)

    return result


def main():
    root_path = environ.get("ROOT_PATH", "/tmp/feedme-posts")
    logger.info(f"Generating index for {root_path}")
    posts = list_posts(root_path)
    page = template_page(misc.bot.name, posts)

    with open(path.join(root_path, "index.html"), "w") as f:
        f.write(page)

    # copy the CSS file
    with open("feedme/templates/default.css", "r") as f:
        css = f.read()

    with open(path.join(root_path, "default.css"), "w") as f:
        f.write(css)

    logger.info("Index generated with %d posts" % len(posts))


if __name__ == "__main__":
    main()
