from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum, Enum
from pathlib import Path
from typing import Final, Optional, Any, Mapping, Self
from urllib.parse import urljoin, quote
from markupsafe import Markup


class BuildReason(IntEnum):
    CREATED = 0
    CHANGED = 1
    UNCHANGED = 2
    DELETED = 3
    VALIDATION = 4


class FileType(Enum):
    """Represents file types supported by generator."""
    OTHER = frozenset() #For invalid file types
    MARKDOWN = frozenset({
        ".md",
        ".mkd",
        ".mdwn",
        ".mdown",
        ".mdtxt",
        ".mdtext",
        ".markdown"
    })
    HTML = frozenset({
        ".html",
        ".htm",
        ".xhtml",
        ".xht"
    })
    YAML = frozenset({
        ".yaml",
        ".yml"
    })

    @classmethod
    def from_suffix(cls, suffix: str) -> "FileType":
        for f_st in cls:
            if suffix.lower() in f_st.value:
                return f_st
        return cls.OTHER

    @classmethod
    def all(cls) -> frozenset["FileType"]:
        return frozenset().union(*(f_st.value for f_st in cls))


@dataclass(frozen=True)
class TemplateContext:
    html: Markup
    table_of_contents: Markup
    title: Markup
    modified: datetime
    url: str
    yml: Mapping[Any, Any]
    now: datetime


class BuildContext:
    """
    Class representing context for use during a page build.

    :ivar source_path: Absolute path to the source file.
    :ivar source_path_lastmod: The last modified date of the source file.
    :ivar dest_path: Absolute path to the destination file.
    :ivar dest_path_lastmod: The last modified date of the destination file if exists.
    :ivar template_path: Absolute path to the template directory.
    :ivar type: FileType representing the file type.
    :ivar url_path: Absolute URL path of output file.
    :ivar validate_only: Do not write build to output file.
    """
    source_path: Final[Path]
    source_path_lastmod: Final[datetime]
    dest_path: Final[Path]
    dest_path_lastmod: Final[Optional[datetime]]
    template_path: Final[Path]
    type: Final[FileType]
    url_path: Final[str]
    validate_only: bool

    def __init__(self, site: "SiteRoot", source: Path, dest: Path): #type: ignore
        self.source_path = site.source_dir.joinpath(source)
        self.dest_path = site.dest_dir.joinpath(dest)
        self.template_path = site.template_dir
        self.type = FileType.from_suffix(self.source_path.suffix)
        self.validate_only = False

        url = dest.as_posix()
        if url.endswith(f"/{site.url_index}") or url == site.url_index:
            url = url.removesuffix(site.url_index)

        self.url_path = urljoin(site.url_base, quote(url))

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
    def build_reason(self) -> BuildReason:
        if self.validate_only:
            return BuildReason.VALIDATION

        if not self.dest_path.exists():
            return BuildReason.CREATED

        if self.source_path_lastmod > self.dest_path_lastmod:
            return BuildReason.CHANGED

        return BuildReason.UNCHANGED

    @property
    def is_modified(self) -> bool:
        reasons = {BuildReason.CREATED, BuildReason.CHANGED, BuildReason.VALIDATION}
        return self.build_reason in reasons
