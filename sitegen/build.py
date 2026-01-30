from __future__ import annotations
import logging
import re
from datetime import datetime, timezone
from io import TextIOWrapper
from charset_normalizer import from_path
from marko import Markdown, MarkoExtension
from marko.block import Document, Heading
from jinja2 import Environment, Template
from typing import Iterable, Final, Any, TypeAlias, Union
from markupsafe import Markup
from abc import ABC, abstractmethod
from .exec import FileTypeError
from .context import BuildContext, TemplateContext, FileType, Metrics
from .templates import PAGE_FALLBACK

logger = logging.getLogger(__name__)

PAGE_DEFAULT: Final[str] = "# {heading}\n{body}"
PAGE_DEFAULT_BODY: Final[str] = "*Nothing here yet...*"

DEFAULT_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {'footnote', 'toc', 'codehilite', 'gfm'}
)

PageTitle: TypeAlias = Markup
PageBody: TypeAlias = Union[Document, str]


class Page(ABC):
    title: PageTitle
    body: PageBody
    template: Template
    build_context: BuildContext
    template_context: TemplateContext
    type: FileType
    metadata: dict[str, Any]
    jinja_env: Environment

    def __init__(self, context: BuildContext, jinja_env: Environment) -> None:
        self.build_context = context
        self.jinja_env = jinja_env

    @abstractmethod
    def parse(self) -> None:
        pass

    def render(self) -> TemplateContext:
        pass

    def read(self) -> str:
        """
        Prepare source file for reading.
        :return: File object as the built-in `open()` function does.
        :raise FileTypeError: Tried to open a non markdown file.
        :raise IOError: If source file cannot be opened for any reason.
        """
        path = self.build_context.source_path
        if not (path.suffix.lower() in self.type.value):
            raise FileTypeError("File not a markdown file.", path.suffix)

        charset = from_path(path).best()
        encoding = (charset.encoding if charset else "utf-8")

        try:
            return path.read_text(errors="ignore", encoding=encoding)
        except OSError as e:
            raise IOError(*e.args) from e

    def write(self) -> int:
        """
        Prepare destination file for writing.
        :return: File object as the built-in `open()` function does.
        :raise IOError: If source file cannot be opened for any reason.
        """
        path = self.build_context.dest_path
        if self.build_context.validate_only:
            return 0

        if not hasattr(self, "template_context"):
            raise RuntimeError("No template_context defined. Have you called `render()`?")

        try:
            content = self.template.render(
                page=self.template_context,
            )

            path.parent.mkdir(parents=True, exist_ok=True)
            return path.write_text(content, errors="ignore", encoding="utf-8")

        except OSError as e:
            raise IOError(*e.args) from e


class MarkdownPage(Page):
    type = FileType.MARKDOWN
    def __init__(self, context: BuildContext, jinja_env: Environment) -> None:
        super().__init__(context, jinja_env)
        self.__marko = Markdown(extensions=DEFAULT_EXTENSIONS)

    def parse(self) -> None:
        """
        Parse the body of this page.
        If the body of the source file is empty, will fallback to default content.
        :return: None
        """

        self.body = self.__marko.parse(
            self.read()
        )

        if len(self.body.children) == 0:
            default_heading = self.build_context.dest_path.stem
            default_body = PAGE_DEFAULT.format(heading=default_heading, body=PAGE_DEFAULT_BODY)
            self.body = self.__marko.parse(default_body)

        self.__extract_title()
        self.metadata = {}
        self.template = self.jinja_env.get_or_select_template(
            ["page.html", PAGE_FALLBACK]
        )

    def __extract_title(self) -> None:
        # Set a default before attempting to get actual title
        title = Heading(
            re.match(Heading.pattern, "# Untitled")
        )

        for e in self.body.children:
            if isinstance(e, Heading) and e.level == 1:
                self.body.children.remove(e)  # type: ignore
                self.title = Markup(
                    self.__marko.renderer.render_children(e)
                )

        self.title = Markup(
            self.__marko.renderer.render_children(title)
        )

    def render(self) -> None:
        if getattr(self, "template_context", None):
            return

        t_c = TemplateContext()
        with Metrics() as metrics:
            metrics["template"] = self.template.name
            t_c.modified = self.build_context.source_path_lastmod
            t_c.yml = self.metadata
            t_c.url = self.build_context.url_path
            t_c.now = datetime.now(timezone.utc)
            t_c.title = self.title

            t_c.html = Markup(
                self.__marko.render(self.body)
            )

            t_c.table_of_contents = Markup(
                self.__marko.renderer.render_toc()
            )

        t_c.metrics = metrics
        self.template_context = t_c