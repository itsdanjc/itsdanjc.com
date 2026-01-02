import logging
import re
from datetime import datetime, timezone
from io import TextIOWrapper
from charset_normalizer import from_path
from marko import Markdown, MarkoExtension
from marko.block import Document, Heading
from jinja2 import Environment, FileSystemLoader, Template
from typing import Iterable, Final, Any
from markupsafe import Markup
from .exec import FileTypeError
from .context import BuildContext, TemplateContext, FileType

logger = logging.getLogger(__name__)
BLANK_PAGE_DEFAULT: Final[str] = "# {heading}\n{body}"
DEFAULT_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {'footnote', 'toc', 'codehilite', 'gfm'}
)
DEFAULT_PAGE_TEMPLATE: Final[Template] = Template(
    "<html><head><title>{{page.title|striptags}}</title>"
    "</head><body><h1>{{page.title}}</h1>"
    "<div style=\"float:right\">{{page.table_of_contents}}</div>"
    "<p>Last Modified: {{page.modified.strftime(\"%d %b %y\")}}"
    "</p>{{page.html}}</body></html>"
)
DEFAULT_PAGE_TEMPLATE.name = "default"


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
    template: Template
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

    def w_open(self) -> TextIOWrapper:
        """
        Prepare destination file for writing.
        :return: File object as the built-in `open()` function does.
        :raise IOError: If source file cannot be opened for any reason.
        """
        path = self.context.dest_path

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            return path.open("w", errors="ignore", encoding="utf-8")

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

    def set_template(self, *templates: str | Template) -> None:
        self.template = self.jinja_env.get_or_select_template(
            [*templates, DEFAULT_PAGE_TEMPLATE]
        )

    def set_title(self) -> Heading:
        # Set a default before attempting to get actual title
        title = Heading(
            re.match(Heading.pattern, "# Heading")
        )

        for e in self.body.children:
            if isinstance(e, Heading) and e.level == 1:
                self.body.children.remove(e) #type: ignore
                return e
        return title

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

        self.title = self.set_title()

    def render(self, *templates: str | Template, **jinja_context) -> None:
        """
        Render this page object to HTML and write it to disk.

        Uses the template `page.html` located in `_fragments` else,
        will fallback to use `DEFAULT_PAGE_TEMPLATE`. Renders the page
        using the current object as context.

        :param templates:
        :param jinja_context: Additional context when rendering.
        :return: None
        """
        self.set_template(*templates, "page.html")

        template_context = TemplateContext(
            html = Markup(
                super().render(self.body)
            ),
            table_of_contents = Markup(
                self.renderer.render_toc()
            ),
            title = Markup(
                self.renderer.render_children(self.title)
            ),
            modified = self.context.source_path_lastmod,
            yml = self.metadata,
            now = datetime.now(timezone.utc)
        )

        with self.w_open() as f:
            html = self.template.render(
                page=template_context, **jinja_context
            )
            f.write(html)

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
    jinja_loader = FileSystemLoader(build_context.template_path)
    jinja_env = Environment(autoescape=True, loader=jinja_loader)

    if not extensions:
        extensions = DEFAULT_EXTENSIONS

    if build_context.type != FileType.MARKDOWN:
        logger.warning("%s is not a Markdown or HTML file.", build_context.source_path.name)
        return

    page = Page(build_context, jinja_env, extensions)
    page.parse(BLANK_PAGE_DEFAULT)

    if page.metadata.get("is_draft", False):
        logger.info("Page %s is draft. Skipping...", build_context.source_path)
        return

    page.render(**jinja_context)
    logger.debug(
        "Successfully built %s using template %s.",
        build_context.source_path.name,
        page.template.name
    )
