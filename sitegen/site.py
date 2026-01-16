from __future__ import annotations
import logging
from pathlib import Path
from typing import Final, List, Optional, Union
from collections.abc import Generator
from .context import BuildContext, FileType

logger = logging.getLogger(__name__)

SOURCE_DIR: Final[Path] = Path("source")
DEST_DIR: Final[Path] = Path("build")
TEMPLATE_DIR: Final[Path] = Path("templates")
URL_BASE: Final[str] = "/"
URL_INDEX: Final[str] = "index.html"

TreeItem: Final[Union] = Union["TreeNode", BuildContext]

class TreeNode:
    path: Final[Path]
    parent: Final[TreeNode | None]
    pages: List[BuildContext]
    dirs: List[TreeNode]

    def __init__(self, path: Path, parent: Optional[TreeNode] = None):
        self.path = path
        self.parent = parent
        self.pages = []
        self.dirs = []

    def __iter__(self) -> Generator[BuildContext, None, None]:
        yield from self.pages
        for sub_dir in self.dirs:
            yield from sub_dir

    def __getitem__(self, path: Path) -> TreeItem:
        for sub_dir in self.yield_dirs():
            if sub_dir.path == path:
                return sub_dir

        for page in self.yield_pages():
            if page.source_path == path:
                return page

        raise KeyError(
            f"Directory or file {path.name} not in {self.path} or a subdirectory"
        )

    def yield_dirs(self) -> Generator[TreeNode, None, None]:
        yield from self.dirs
        for sub_dir in self.dirs:
            yield from sub_dir.yield_dirs()

    def yield_pages(self) -> Generator[BuildContext, None, None]:
        yield from self.pages
        for sub_dir in self.dirs:
            yield from sub_dir.yield_pages()


class TreeBuilder:
    site: Final[SiteRoot]
    node: TreeNode
    node_path: Path
    node_dir_list: List[str]
    node_file_list: List[str]
    node_not_root: bool

    def __init__(self, site: SiteRoot):
        self.site = site
        self.node = site.tree

    def build(self) -> None:
        for curr_dir, dir_list, file_list in self.site.source_dir.walk():
            self.node_path = curr_dir
            self.node_dir_list = dir_list
            self.node_file_list = file_list

            self.node_not_root = (curr_dir != self.site.tree.path)

            if self.node_not_root:
                self.node = self.site.tree[curr_dir]

            self.create_directory_nodes()
            self.create_file_nodes()

    def create_directory_nodes(self):
        for sub_dir in self.node_dir_list:
            node_path = Path(self.node_path, sub_dir)
            self.node.dirs.append(
                TreeNode(node_path, parent=self.node)
            )

    def create_file_nodes(self):
        for file in self.node_file_list:
            file_path = Path(self.node_path, file).relative_to(
                self.site.source_dir
            )

            dest = file_path.with_suffix(".html")

            if not (file_path.suffix.lower() in self.site.valid_ext):
                continue

            context = BuildContext(
                site=self.site,
                source=file_path,
                dest=dest
            )

            self.node.pages.append(context)


class SiteRoot:
    """
    This class represents the root of the site.
    """
    root: Final[Path]
    tree: TreeNode
    valid_ext: Final[frozenset[str]] = FileType.all()
    source_dir: Final[Path]
    dest_dir: Final[Path]
    template_dir: Final[Path]
    url_base: Final[str] = URL_BASE
    url_index: Final[str] = URL_INDEX

    def __init__(self, path: Path):
        self.root = path
        self.source_dir = path.joinpath(SOURCE_DIR)
        self.dest_dir = path.joinpath(DEST_DIR)
        self.template_dir = path.joinpath(TEMPLATE_DIR)
        self.tree = TreeNode(self.source_dir)

    def clean_dest(self) -> List[Path]:
        total_removed = []
        for file in self.dest_dir.glob("**"):
            if not (file.is_file() and file.suffix.lower() in FileType.HTML.value):
                continue

            logger.debug("Cleanup deleted %s", file)
            file.unlink(missing_ok=True)
            total_removed.append(file)

        return total_removed
