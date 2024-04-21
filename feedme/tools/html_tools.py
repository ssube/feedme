from os import path

from jinja2 import Environment, PackageLoader, select_autoescape

from feedme.data import get_save_path

DEFAULT_TEMPLATE = "default.html.j2"


def template_post(
    images, description="", title="", mature=False, template=None, destination=None
):
    """
    Generate a webpage for a post using one of the HTML templates.
    """

    if template is None:
        template = DEFAULT_TEMPLATE

    if destination is None:
        destination = path.join(get_save_path(), "post.html")

    env = Environment(
        loader=PackageLoader("feedme", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template)
    result = template.render(
        title=title, description=description, images=images, mature=mature
    )

    with open(destination, "wb") as f:
        f.write(result.encode("utf-8"))

    return result
