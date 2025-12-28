import logging
from pathlib import Path
from datetime import datetime, timezone
from marko import Markdown, MarkoExtension
from marko.block import Document, Heading
from jinja2 import Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateSyntaxError
from typing import Iterable, Final, Any
from .templates import (
    DEFAULT_PAGE_TEMPLATE,
    BLANK_PAGE_DEFAULT
)
from .context import BuildContext, FileType
from .exec import (
    MarkdownParseException,
    MarkdownRenderException,
    MarkdownTemplateException
)

logger = logging.getLogger(__name__)
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
            extensions: Iterable[str | MarkoExtension] | None = None,
    ):
        """
        Initialize a page from a Markdown document.

        **Note:** In most cases, you would not need to access this class directly,
        instead use `sitegen.build()` which handles most of what this class
        does in a single call.

        This class sets up the Markdown parser with the requested extensions and
        associates the page with its source file and rendering environment.
        The document contents are not rendered until explicitly requested.

        :param path: Path to the source Markdown file.
        :param jinja_env: Jinja2 environment used for rendering templates.
        :param extensions: Optional iterable of Marko extension names or
            extension instances to enable for Markdown parsing.

        *See Also:* ``sitegen.build()``
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
        try:
            with self.document_path.open("r", errors='replace') as f:
                doc_body: str = f.read()
                self.metadata = dict()
                self.body = self.parse(doc_body)
        except FileNotFoundError as e:
            raise MarkdownParseException(
                "Unable to open %s.", self.document_path,
            ) from e

        if len(self.body.children) == 0:
            logger.warning(
                "%s has empty body and should probably be set to draft.",
                self.document_path.name
            )
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

        :raises MarkdownRenderException: if rendering fails.
        :raises MarkdownTemplateException: if rendering fails, specifically with a template.
        """
        template: Template
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            template = self.jinja_env.get_or_select_template(
                ["page.html", DEFAULT_PAGE_TEMPLATE]
            )

            with dest.open("w", encoding="utf-8") as f:
                render_result: str = template.render(page=self, **jinja_context)
                f.write(render_result)


        except TemplateSyntaxError as e:
            raise MarkdownTemplateException(
                "%s in template %s line %d", e.message, e.lineno, e.name
            ) from e

        except Exception as e:
            raise MarkdownRenderException(
                "".join(e.args)
            ) from e

        logger.debug(
            "Successfully built %s using template %s.",
            self.document_path.name,
            template.name
        )


    #Methods dest be used in jinja templates
    def to_html(self):
        return self.render(self.body)

    def get_title(self):
        return self.renderer.render_children(self.title)


def build(
        build_context: BuildContext,
        extensions: Iterable[str | MarkoExtension] | None = None,
        **jinja_context: Any
) -> None:
    """
    Build a page from a Markdown document.

    If no extensions are provided, the default extension list will be used.

    :param build_context: BuildContext instance.
    :param extensions: Optional iterable of Marko extension names or
            extension instances to enable for Markdown parsing.
    :param jinja_context: Additional context when rendering.
    :return: None
    """
    jinja_env = Environment(
        autoescape=True,
        loader=FileSystemLoader(build_context.template_path),
    )

    if not extensions:
        extensions = DEFAULT_EXTENSIONS

    if build_context.type != FileType.MARKDOWN:
        logger.warning("%s is not a Markdown or HTML file.", build_context.source_path.name)
        return

    logger.info("Building page %s.", build_context.source_path.name)
    page = Page(build_context.source_path, jinja_env, extensions)
    page.read_parse()

    if page.metadata.get("is_draft", False):
        logger.info("Page %s is draft. Skipping...", build_context.source_path)
        return

    page.render_write(build_context.dest_path, **jinja_context)
