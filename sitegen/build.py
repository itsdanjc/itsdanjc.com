from pathlib import Path
from datetime import datetime, timezone
from marko import Markdown, MarkoExtension
from marko.block import Document, Heading
from jinja2 import Environment
from typing import Iterable, Final, Any
from .templates import DEFAULT_PAGE_TEMPLATE, BLANK_PAGE_DEFAULT

DEFAULT_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {'footnote', 'toc', 'codehilite', 'gfm'}
)

class Page(Markdown):
    """
    This class represents a single renderable page within the site.
    It extends :class:`marko.Markdown`.

    A ``Page`` instance typically corresponds to a single source document
    on disk and is rendered using a Jinja2 template.

    :ivar title: Parsed top-level heading used as the page title.
    :ivar body: Parsed Markdown document body.
    :ivar document_path: Path to the source document.
    :ivar metadata: Page metadata defined at the top of each file.
    :ivar last_modified: Timestamp of the last modification of the source file.
    :ivar jinja_env: Jinja2 environment used for template rendering.
    """

    title: Heading
    body: Document
    document_path: Path
    metadata: dict[str, Any]
    last_modified: datetime
    jinja_env: Environment

    def __init__(
            self,
            path: Path,
            jinja_env: Environment,
            extensions: Iterable[str | MarkoExtension] | None = DEFAULT_EXTENSIONS,
    ):
        """
        Initialize a page from a Markdown document.

        This sets up the Markdown parser with the requested extensions and
        associates the page with its source file and rendering environment.
        The document contents are not rendered until explicitly requested.

        :param path: Path to the source Markdown file.
        :param jinja_env: Jinja2 environment used for rendering templates.
        :param extensions: Optional iterable of Marko extension names or
            extension instances to enable for Markdown parsing.
        """
        super().__init__(extensions=extensions)
        self.jinja_env = jinja_env
        self.document_path = path

    def read_parse(self, default: str | None = None) -> None:
        """
        Read and parse the file represented by this object from disk.

        Uses source path `self.document_path`.

        If the body of the source file is empty, will fallback to default content.
        :return: None
        """
        with self.document_path.open("r", errors='replace') as f:
            doc_body: str = f.read()
            self.body = self.parse(doc_body)

        if len(self.body.children) == 0:
            default_body: str = BLANK_PAGE_DEFAULT.format(
                heading=self.document_path.stem.title(),
                body=default,
            )
            self.body: Document = self.parse(default_body)

        self.last_modified = datetime.fromtimestamp(
            self.document_path.stat().st_mtime,
            tz=timezone.utc,
        )

        first_child = self.body.children[0]
        if isinstance(first_child, Heading):
            self.title = first_child
            self.body.children = self.body.children[1:]

    def render_write(self, dest: Path, **jinja_context) -> None:
        """
        Render this page object to HTML and write it to disk.

        Uses the template `page.html` located in `_fragments` else,
        will fallback to use `DEFAULT_PAGE_TEMPLATE`. Renders the page
        using the current object as context.

        :param dest: Destination file path.
        :param jinja_context: Additional context when rendering.
        :return: None
        """
        template = self.jinja_env.get_or_select_template(
            ["page.html", DEFAULT_PAGE_TEMPLATE]
        )

        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8") as f:
            render_result: str = template.render(page=self, **jinja_context)
            f.write(render_result)


    #Methods dest be used in jinja templates
    def to_html(self):
        return self.render(self.body)

    def get_title(self):
        return self.renderer.render_children(self.title)