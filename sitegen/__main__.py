import argparse
import logging
import sys
import json
from enum import Enum
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Optional, Final
from jinja2 import TemplateError
from sitegen.context import Metrics
from .log import configure_logging
from .site import SiteRoot, TreeBuilder, SortKey
from .cli import BuildStats
from . import __version__, __author__

CLI_NAME = "sitegen"
CLI_HEADER_MSG: Final[str] = f"{CLI_NAME} {__version__}, by {__author__}"
CLI_DESC: Final[str] = "Epilogue"

logger = logging.getLogger(__name__)
cwd = Path.cwd()

class TreeFormat(Enum):
    TREE = "tree"
    URL = "url"
    JSON = "json"

def add_commands(ap) -> None:
    # Build command
    build_cmd = ap.add_parser("build", help="Build the site.")
    build_cmd.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force rebuild of all pages"
    )
    build_cmd.add_argument(
        "-c",
        "--clean",
        action="store_true",
        help="clear the build directory, then build"
    )
    build_cmd.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="run as normal. but don't create build files"
    )
    build_cmd.add_argument(
        "--no-rss",
        action="store_true",
        help="do not update rss feed."
    )
    build_cmd.add_argument(
        "--no-sitemap",
        action="store_true",
        help="do not update sitemap feed."
    )
    build_cmd.add_argument(
        "-r",
        "--site-root",
        type=Path,
        default=cwd,
        metavar="PATH",
        help="location of webroot, if not at the current working directory"
    )

    # Tree command
    tree_cmd = ap.add_parser("tree", help="View a directory tree of the site.")
    tree_cmd.add_argument(
        "-i",
        "--reindex",
        action="store_true",
        help="ignore cache and reindex"
    )
    tree_cmd.add_argument(
        "-f",
        "--format",
        choices=[i.value for i in TreeFormat],
        default=TreeFormat.TREE.value,
        help="output in this format"
    )
    tree_cmd.add_argument(
        "-s",
        "--sort",
        choices=["type", "path", "lastmod", "lastbuild"],
        help="sort the result (not available with --format tree)"
    )
    tree_cmd.add_argument(
        "-m",
        "--max",
        type=int,
        metavar="INTEGER",
        help="""only return up to this number of entries, 
        can be a performance benefit (not available with --format tree)"""
    )
    tree_cmd.add_argument(
        "-r",
        "--site-root",
        type=Path,
        default=cwd,
        metavar="PATH",
        help="location of webroot, if not at the current working directory"
    )


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog=CLI_NAME, description=CLI_DESC)
    commands = parser.add_subparsers(title="commands", dest="commands", required=True)

    # Global Arguments
    parser.add_argument("-v", "--verbose", action="store_true", help="Show more info in logs")
    parser.add_argument("--version", action="version", version=__version__)

    add_commands(commands)
    args = parser.parse_args(argv)

    configure_logging(args.verbose)
    logger.info("%s\n", CLI_HEADER_MSG)

    func_args = tuple()
    func: Callable[..., int] = lambda: 0

    match args.commands:
        case "build":
            func = build
            func_args = (
                args.force, args.site_root, args.clean,
                args.dry_run, args.no_rss, args.no_sitemap
            )

        case "tree":
            func = tree
            func_args = (
                args.site_root, args.reindex, args.format,
                args.sort, args.max
            )

    try:
        sys.exit( func(*func_args) )
    except KeyboardInterrupt:
        sys.exit(0)

def tree(directory: Path, reindex: bool, format: str, sort: str, max_display: int) -> int:
    site = SiteRoot(directory.resolve())

    if not site.source_dir.exists():
        return 0

    # Index site
    delta = timedelta(microseconds=1) if reindex else None
    builder = TreeBuilder(site, delta)
    builder_time = builder.metrics["total_time"]
    logger.info("Indexed site in %.2fs.", builder_time)
    del builder

    def clamp(min_v: int, max_v: int, v: int) -> int:
        if not v:
            return max_v
        return max(min_v, min(v, max_v))

    def tree_list() -> list:
        match sort:
            case "type":
                return site.tree.sort(SortKey.BUILD_REASON) #type: ignore
            case "path":
                return site.tree.sort(SortKey.PATH) #type: ignore
            case "lastmod":
                return site.tree.sort(SortKey.LAST_MODIFIED) #type: ignore
            case "lastbuild":
                return site.tree.sort(SortKey.LAST_BUILD_DATE) #type: ignore
            case _:
                return [*site.tree]

    def json_format():
        results = []
        for p in tree_l[:max_display]:
            results.append({
                "url": p.build_context.url_path,
                "source": str(p.build_context.source_path),
                "lastModified": p.build_context.source_path_lastmod.isoformat(),
                "type": p.build_context.type.name.lower(),
            })

        print(json.dumps(results, indent=3), flush=True)

    def url_format():
        for page in tree_l[:max_display]:
            print(page.build_context.url_path, flush=True)

    with Metrics() as metrics:
        max_display = clamp(1, len(site.tree), max_display)
        tree_l = tree_list()

        if format == TreeFormat.URL.value:
            url_format()

        elif format == TreeFormat.JSON.value:
            json_format()

        elif format == TreeFormat.TREE.value:
            raise NotImplementedError()

    time = metrics["total_time"] + builder_time
    logger.info(
        f"Done - about %d results in %.2fs",
        min(max_display, len(tree_l)) if max_display else len(tree_l),
        time
    )
    return 0

def build(
        force: bool, directory: Path, perform_clean: bool,
        dry_run: bool, no_rss: bool, no_sitemap: bool
) -> int:
    site = SiteRoot(directory.resolve())

    if not site.source_dir.exists():
        logger.error("No site at %s", site.root)
        return 1

    logger.info("Building site at %s", site.root)
    index_cache_duration = (
        timedelta(seconds=0) if perform_clean or dry_run
        else timedelta(minutes=2.5)
    )

    with BuildStats() as build_stats:
        builder = TreeBuilder(site, index_cache_duration)
        logger.info("Indexed site in %.2fs.", builder.metrics["total_time"])
        del builder

        if perform_clean:
            logger.info("Performing cleanup.")
            site.clean_dest()

        for page in site.tree:
            name = page.build_context.source_path.name
            page.build_context.validate_only = dry_run

            page.parse()
            if not (page.build_context.is_modified or force or dry_run):
                logger.debug("Found unmodified %s", name)
                continue

            logger.info("Building page %s", name)

            try:
                page.render()
                page.write()
                build_stats.add_stat(page.build_context.build_reason)

            except (OSError, TemplateError, FileExistsError) as e:
                build_stats.errors += 1
                logger.exception("Failed to build", exc_info=e)
                continue

        if not (no_rss or dry_run):
            rss_path = site.dest_dir.joinpath("feed.xml")
            site.make_rss(rss_path)

        if not (no_sitemap or dry_run):
            sitemap_path = site.dest_dir.joinpath("sitemap.xml")
            site.make_sitemap(sitemap_path)

    logger.info(build_stats.summary())
    return 0

if __name__ == "__main__":
    main()
