import logging, os
from pathlib import Path
from typing import Final, List
from .context import BuildContext, FileType

logger = logging.getLogger(__name__)


class SiteRoot:
    """
    This class represents the root of the site.
    """
    root_path: Final[Path]
    tree: List[BuildContext]

    def __init__(self, path: Path):
        """

        :param path: Path to the root of the site.
        """
        self.root_path = path
        self.tree = []

    def make_tree(self) -> None:
        md_dir = self.root_path.joinpath("_public")
        for dir_in, _, files in os.walk(md_dir):
            sub_dir = Path(dir_in)
            for file in files:
                file_path = sub_dir.joinpath(file)
                file_path = file_path.relative_to(md_dir)
                dest = file_path.parent.joinpath(
                    file_path.stem + ".html",
                )
                context = BuildContext(
                    cwd=self.root_path,
                    source=file_path,
                    dest=dest
                )

                if not context.type in {FileType.HTML, FileType.MARKDOWN}:
                    continue

                logger.debug("Found %s", file_path)
                self.tree.append(context)
