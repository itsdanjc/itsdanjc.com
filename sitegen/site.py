import logging
from pathlib import Path
from typing import Final, Generator, Set
from .context import BuildContext, FileType, SOURCE_DIR

logger = logging.getLogger(__name__)


class SiteRoot:
    """
    This class represents the root of the site.
    """
    root_path: Final[Path]
    tree: Set[BuildContext]
    valid_ext: Final[frozenset[str]] = frozenset(
        FileType.HTML.value | FileType.MARKDOWN.value
    )

    def __init__(self, path: Path):
        """

        :param path: Path to the root of the site.
        """
        self.root_path = path

    def tree_iter(self, follow_links: bool = False) -> Generator[BuildContext, None, None]:
        md_dir = self.root_path.joinpath(SOURCE_DIR)

        for file in md_dir.glob("**", recurse_symlinks=follow_links):
            if not (file.is_file() and file.suffix.lower() in self.valid_ext):
                continue

            file_path = file.relative_to(md_dir)
            dest = file_path.parent.joinpath(
                file_path.stem + ".html",
            )

            yield BuildContext(
                cwd=self.root_path,
                source=file_path,
                dest=dest
            )

