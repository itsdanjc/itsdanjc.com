from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum, Enum
from pathlib import Path
from typing import Final, Optional, Any, Mapping
from markupsafe import Markup

class BuildReason(IntEnum):
    CREATED = 0
    CHANGED = 1
    UNCHANGED = 2
    DELETED = 3


class FileType(Enum):
    MARKDOWN = {".md", ".markdown"}
    HTML = {".html", ".htm"}
    NOT_PARSEABLE = set()


@dataclass(frozen=True)
class TemplateContext:
    html: Markup
    table_of_contents: Markup
    title: Markup
    modified: datetime
    yml: Mapping[Any, Any]
    now: datetime


class BuildContext:
    """
    Initialize a build context from relative paths.

    :ivar curr_working_dir: Current working directory used as the base for all paths.
    :ivar source_path: Path to the source content directory relative to webroot.
    :ivar source_path_lastmod: The last modified date of the source file.
    :ivar dest_path: Path to the output destination directory relative to webroot.
    :ivar dest_path_lastmod: The last modified date of the destination file if exists.
    :ivar template_path: Path to the template directory relative to webroot.
    """
    curr_working_dir: Final[Path]
    source_path: Final[Path]
    source_path_lastmod: Final[datetime]
    dest_path: Final[Path]
    dest_path_lastmod: Final[Optional[datetime]]
    template_path: Final[Path]

    def __init__(self, cwd: Path, source: Path, dest: Path):
        self.curr_working_dir = cwd
        self.source_path = cwd.joinpath("_public", source)
        self.dest_path = cwd.joinpath(dest)
        self.template_path = cwd.joinpath("_fragments")

        self.source_path_lastmod = datetime.fromtimestamp(
            self.source_path.stat().st_mtime,
            tz=timezone.utc
        )

        self.dest_path_lastmod = datetime.fromtimestamp(
            self.dest_path.stat().st_mtime
            if self.dest_path.exists()
            else 0,
            tz=timezone.utc,
        )

    @property
    def type(self) -> FileType:
        match_str = self.source_path.suffix.lower()
        if match_str in FileType.MARKDOWN.value:
            return FileType.MARKDOWN

        if match_str in FileType.HTML.value:
            return FileType.HTML

        return FileType.NOT_PARSEABLE

    @property
    def build_reason(self) -> BuildReason:
        if not self.dest_path.exists():
            return BuildReason.CREATED

        if self.source_path_lastmod > self.dest_path_lastmod:
            return BuildReason.CHANGED

        return BuildReason.UNCHANGED

    @property
    def is_modified(self) -> bool:
        return self.build_reason in {BuildReason.CREATED, BuildReason.CHANGED}
