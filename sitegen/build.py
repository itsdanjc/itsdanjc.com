import logging
from io import TextIOWrapper
from charset_normalizer import from_path
from pathlib import Path
from marko import Markdown, MarkoExtension
from marko.block import Document, Heading
from jinja2 import Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateSyntaxError
from typing import Iterable, Final, Any, override
from .exec import FileTypeError
from .templates import (
    DEFAULT_PAGE_TEMPLATE,
    BLANK_PAGE_DEFAULT
)
from .context import BuildContext, FileType

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
    :ivar context: Path to the source document.
    :ivar metadata: Page metadata defined at the top of each file.
    :ivar jinja_env: Jinja2 environment used for template rendering.
    """

    title: Heading
    body: Document
    context: BuildContext
    metadata: dict[str, Any]
    jinja_env: Environment

    def __init__(
            self,
            context: BuildContext,
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

        :param context: Path to the source Markdown file.
        :param jinja_env: Jinja2 environment used for rendering templates.
        :param extensions: Optional iterable of Marko extension names or
            extension instances to enable for Markdown parsing.

        *See Also:* ``sitegen.build()``
        """
        super().__init__(extensions=extensions)
        self.jinja_env = jinja_env
        self.context = context

    def r_open(self) -> TextIOWrapper:
        """
        Prepare source file for reading.
        :return: File object as the built-in `open()` function does.
        :raise FileTypeError: Tried to open a non markdown file.
        :raise IOError: If source file cannot be opened for any reason.
        """
        path = self.context.source_path
        if not (path.suffix.lower() in FileType.MARKDOWN.value):
            raise FileTypeError("File not a markdown file.", path.suffix)

        try:
            charset = from_path(path).best()
            encoding = (charset.encoding if charset else "utf-8")
            return path.open("r", errors="ignore", encoding=encoding)

        except OSError as e:
            raise IOError(*e.args) from e

    def read(self) -> tuple[str, str]:
        """
        Return the contents of the file as strings.
        :raise FileTypeError: Tried to open a non markdown file.
        :raise IOError: If source file cannot be opened for any reason.
        :return: A tuple containing the yml header and the body.
        """
        body: str
        with self.r_open() as f:
            body = f.read()

        self.metadata = dict() # TODO: Parse yml at start of file.
        return "", body

    @override
    def parse(self, default: str | None = None) -> None:
        """
        Parse the body of this page.
        If the body of the source file is empty, will fallback to default content.
        :return: None
        """
        yml, body = self.read()
        self.body = super().parse(body)

        if len(self.body.children) == 0:
            self.body = super().parse(default)
            logger.warning(
                "%s has empty body and should probably be set to draft.",
                self.context.source_path.name
            )

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
            raise OSError(
                "%s in template %s line %d", e.message, e.lineno, e.name
            ) from e

        except Exception as e:
            raise OSError(
                "".join(e.args)
            ) from e

        logger.debug(
            "Successfully built %s using template %s.",
            self.context.source_path.name,
            template.name
        )

    #Methods dest be used in jinja templates
    def to_html(self):
        return self.render(self.body)

    def get_title(self):
        if not hasattr(self, "title"):
            return "Untitled"
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
    page = Page(build_context, jinja_env, extensions)
    page.parse(BLANK_PAGE_DEFAULT)

    if page.metadata.get("is_draft", False):
        logger.info("Page %s is draft. Skipping...", build_context.source_path)
        return

    page.render_write(build_context.dest_path, **jinja_context)
