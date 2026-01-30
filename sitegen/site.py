from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Final, List, Union, TypeAlias, Any, Type
from collections.abc import Generator, Callable
from jinja2 import Environment, FileSystemLoader, Template
from .context import FileType, BuildContext, Metrics
from .templates import RSS_FALLBACK, SITEMAP_FALLBACK
from .build import MarkdownPage, DEFAULT_EXTENSIONS
from .exec import FileTypeError

logger = logging.getLogger(__name__)

SOURCE_DIR: Final[Path] = Path("source")
DEST_DIR: Final[Path] = Path("build")
TEMPLATE_DIR: Final[Path] = Path("templates")
URL_BASE: Final[str] = "https://itsdanjc.com"
URL_INDEX: Final[str] = "index.html"

Page: TypeAlias = Union[MarkdownPage]
TreeItem: TypeAlias = Union["TreeNode", Page]


class SortKey(Enum):
    """Sort key methods. For TreeNode.sort()"""
    BUILD_REASON = lambda page: page.build_context.build_reason
    FILE_TYPE = lambda page: page.build_context.type
    PATH = lambda page: page.build_context.url_path
    LAST_MODIFIED = lambda page: page.build_context.source_path_lastmod
    LAST_BUILD_DATE = lambda page: page.build_context.dest_path_lastmod


class TreeNode:
    path: Final[Path]
    parent: Final[TreeNode | None]
    pages: list[Page]
    sub_dirs: list[TreeNode]

    def __init__(self, path: Path, parent: TreeNode | None = None):
        self.path = path
        self.parent = parent
        self.pages = []
        self.sub_dirs = []

    def __iter__(self) -> Generator[Page, None, None]:
        yield from self.pages
        for s_d in self.sub_dirs:
            yield from s_d

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __contains__(self, item: TreeItem) -> bool:
        if isinstance(item, Page):
            return any(i for i in self)

        if isinstance(item, TreeNode):
            return any(i for i in self.walk())

        return False

    def __getitem__(self, path: Path) -> TreeItem:
        if self.path == path:
            return self

        for page in self:
            if page.build_context.source_path == path:
                return page

        for s_d in self.walk():
            if s_d.path == path:
                return s_d

        raise KeyError(
            f"Directory or file {path} not in {self.path} or any subdirectory"
        )

    def walk(self) -> Generator[TreeNode, None, None]:
        """Return a generator of all subdirectories of self"""
        yield from self.sub_dirs
        for s_d in self.sub_dirs:
            yield from s_d.walk()

    def sort(self, key: Callable[[Page], Any], reverse: bool | None = True) -> List[Page]:
        """Return a sorted copy of self."""
        return sorted(
            self,
            key=key,
            reverse=reverse
        )


class PageNode:
    _registry: dict[FileType, Type[Page]] = {
        FileType.MARKDOWN: MarkdownPage,
        # FileType.HTML: HtmlPage,au
        # FileType.YAML: YamlPage,
    }

    @classmethod
    def register(cls, file_type: FileType, page_cls: Type[Page]) -> None:
        cls._registry[file_type] = page_cls

    @classmethod
    def create(cls, context: BuildContext, jinja_env: Environment) -> Page:
        try:
            page_cls = cls._registry[context.type]
        except KeyError:
            raise FileTypeError("Invalid file type", "")

        return page_cls(context, jinja_env)


class TreeBuilder:
    site: Final[SiteRoot]
    valid_ext: Final[frozenset[str]] = FileType.all()
    node: TreeNode
    node_path: Path
    node_dir_list: List[str]
    node_file_list: List[str]
    node_not_root: bool
    metrics: Metrics

    def __init__(self, site: SiteRoot):
        self.site = site
        self.node = site.tree

        with Metrics() as self.metrics:
            for curr_dir, dir_list, file_list in os.walk(self.site.source_dir):
                self.node_path = Path(curr_dir)
                self.node_dir_list = dir_list
                self.node_file_list = file_list

                self.node_not_root = (curr_dir != self.site.tree.path)

                if self.node_not_root:
                    self.node = self.site.tree[self.node_path]

                self.create_directory_nodes()
                self.create_file_nodes()

    def create_directory_nodes(self):
        for sub_dir in self.node_dir_list:
            node_path = Path(self.node_path, sub_dir)
            self.node.sub_dirs.append(
                TreeNode(node_path, parent=self.node)
            )

    def create_file_nodes(self):
        for file in self.node_file_list:
            file_path = Path(self.node_path, file).relative_to(
                self.site.source_dir
            )

            dest = file_path.with_suffix(".html")

            if not (file_path.suffix.lower() in self.valid_ext):
                continue

            context = BuildContext(
                site=self.site,
                source=file_path,
                dest=dest,
                env=self.site.env
            )

            self.node.pages.append(
                PageNode.create(context, self.site.env)
            )


class SiteRoot:
    """
    This class represents the root of the site.
    """
    root: Final[Path]
    tree: TreeNode
    source_dir: Final[Path]
    dest_dir: Final[Path]
    template_dir: Final[Path]
    env: Final[Environment]
    url_base: Final[str] = URL_BASE
    url_index: Final[str] = URL_INDEX

    def __init__(self, path: Path):
        self.root = path
        self.source_dir = path.joinpath(SOURCE_DIR)
        self.dest_dir = path.joinpath(DEST_DIR)
        self.template_dir = path.joinpath(TEMPLATE_DIR)
        self.tree = TreeNode(self.source_dir)
        self.env = Environment(
            autoescape=True,
            auto_reload=False,
            loader=FileSystemLoader(self.template_dir)
        )

    def clean_dest(self) -> List[Path]:
        total_removed = []
        for file in self.dest_dir.glob("**"):
            if not (file.is_file() and file.suffix.lower() in FileType.HTML.value):
                continue

            logger.debug("Cleanup deleted %s", file)
            file.unlink(missing_ok=True)
            total_removed.append(file)

        return total_removed

    def render_index(self, template: Template) -> str:
        tree = []
        for node in self.tree.sort(SortKey.LAST_MODIFIED):
            node.render()
            tree.append(node.template_context)

        return template.render(
            site=self,
            tree=tree,
            now=datetime.now(tz=timezone.utc)
        )

    def make_rss(self, out: Path) -> None:
        rss_template = self.env.get_or_select_template(
            ["feed.xml", RSS_FALLBACK]
        )

        rss_feed = self.render_index(rss_template)
        out.write_text(rss_feed)

    def make_sitemap(self, out: Path) -> None:
        sitemap_template = self.env.get_or_select_template(
            ["sitemap.xml", SITEMAP_FALLBACK]
        )

        sitemap = self.render_index(sitemap_template)
        out.write_text(sitemap)
