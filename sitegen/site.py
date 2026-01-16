from __future__ import annotations
import logging
from pathlib import Path
from typing import Final, List, Optional
from collections.abc import Generator
from .context import BuildContext, FileType

logger = logging.getLogger(__name__)

SOURCE_DIR: Final[Path] = Path("source")
DEST_DIR: Final[Path] = Path("build")
TEMPLATE_DIR: Final[Path] = Path("templates")
URL_BASE: Final[str] = "/"
URL_INDEX: Final[str] = "index.html"


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


class SiteRoot:
    """
    This class represents the root of the site.
    """
    root_path: Final[Path]
    tree: TreeNode
    valid_ext: Final[frozenset[str]] = FileType.all()
    source_dir: Final[Path]
    dest_dir: Final[Path]
    template_dir: Final[Path]
    url_base: Final[str] = URL_BASE
    url_index: Final[str] = URL_INDEX

    def __init__(self, path: Path):
        self.root_path = path
        self.tree = TreeNode(path)
        self.source_dir = path.joinpath(SOURCE_DIR)
        self.dest_dir = path.joinpath(DEST_DIR)
        self.template_dir = path.joinpath(TEMPLATE_DIR)

    def tree_iter(self) -> Generator[BuildContext, None, None]:
        md_dir = self.root_path.joinpath(SOURCE_DIR)

        for file in md_dir.glob("**"):
            if not (file.is_file() and file.suffix.lower() in self.valid_ext):
                continue

            file_path = file.relative_to(md_dir)
            dest = file_path.with_suffix(".html")

            yield BuildContext(
                site=self,
                source=file_path,
                dest=dest
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
