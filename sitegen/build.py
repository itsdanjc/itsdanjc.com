from pathlib import Path
from datetime import datetime
from marko import Markdown
from marko.block import Document, Heading
from jinja2 import Environment, Template

BLANK_PAGE_DEFAULT = "# {heading}\n{body}"
DEFAULT_PAGE_TEMPLATE = "<h1>{{page.get_title()|safe}}</h1>{{page.to_html()|safe}}"
ENABLED_MARKO_EXTENSIONS = frozenset(
    {'footnote', 'toc', 'codehilite', 'gfm'}
)


class Page(Markdown):
    """
    Object representing a single page within the site.
    A subclass of `marko.Markdown`.
    """

    title: Heading
    body: Document
    document_path: Path
    is_draft: bool
    default_when_empty: str
    last_modified: datetime

    def __init__(self, path: Path, default: str | None = ""):
        super().__init__(extensions=ENABLED_MARKO_EXTENSIONS)
        self.document_path = path
        self.default_when_empty = BLANK_PAGE_DEFAULT.format(
            heading=self.document_path.stem.title(),
            body=default,
        )

    def read(self) -> None:
        """
        Read and parse the markdown file at located at `self.document_path`.
        :return:
        """
        with self.document_path.open("r", errors='replace') as f:
            self.body = self.parse(f.read())

        if len(self.body.children) == 0:
            self.body = self.parse(self.default_when_empty)

        first_child = self.body.children[0]
        if isinstance(first_child, Heading):
            self.title = first_child
            self.body.children = self.body.children[1:]

    def write(self, to: Path, jinja_env: Environment) -> None:
        template = jinja_env.get_or_select_template(
            ["page.html", Template(DEFAULT_PAGE_TEMPLATE)]
        )

        to = to.joinpath(self.document_path.stem + ".html")
        to.parent.mkdir(parents=True, exist_ok=True)
        with to.open("w", encoding="utf-8") as f:
            f.write(template.render(page=self))


    #Methods to be used in jinja templates
    def to_html(self):
        return self.render(self.body)

    def get_title(self):
        return self.renderer.render_children(self.title)