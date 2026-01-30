import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Final
from jinja2 import TemplateError
from .log import configure_logging
from .site import SiteRoot, TreeBuilder
from .cli import BuildStats
from . import __version__, __author__

CLI_NAME = "sitegen"
CLI_HEADER_MSG: Final[str] = f"{CLI_NAME} {__version__}, by {__author__}"
CLI_DESC: Final[str] = "Epilogue"

logger = logging.getLogger(__name__)
cwd = Path.cwd()

def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog=CLI_NAME, description=CLI_DESC)
    commands = parser.add_subparsers(title="commands", dest="commands", required=True)

    # Global Arguments
    parser.add_argument("-v", "--verbose", action="store_true", help="Show more info in logs")
    parser.add_argument("--version", action="version", version=__version__)

    # Build command
    build_cmd = commands.add_parser("build", help="Build the site.")
    build_cmd.add_argument(
        "-f","--force", action="store_true",
        help="force rebuild of all pages")
    build_cmd.add_argument(
        "-c","--clean", action="store_true",
        help="clear the build directory, then build")
    build_cmd.add_argument(
        "-d","--dry-run", action="store_true",
        help="run as normal. but don't create build files")
    build_cmd.add_argument(
        "--no-rss", action="store_true",
        help="do not update rss feed.")
    build_cmd.add_argument(
        "--no-sitemap", action="store_true",
        help="do not update sitemap feed.")
    build_cmd.add_argument(
        "-r", "--site-root", type=Path, default=cwd, metavar="PATH",
        help="location of webroot, if not at the current working directory")

    args = parser.parse_args(argv)
    print(CLI_HEADER_MSG, end="\n\n")
    configure_logging(args.verbose)
    try:
        if args.commands == "build":
            build(
                args.force,
                args.site_root,
                args.clean,
                args.dry_run,
                args.no_rss,
                args.no_sitemap
            )
    except KeyboardInterrupt:
        sys.exit(0)



def build(
        force: bool,
        directory: Path,
        perform_clean: bool,
        dry_run: bool,
        no_rss: bool,
        no_sitemap: bool
) -> None:
    site = SiteRoot(directory.resolve())
    logger.info("Building site at %s", site.root)

    with BuildStats() as build_stats:
        logger.info("Indexing source directory.")
        TreeBuilder(site)


        if perform_clean:
            logger.info("Performing cleanup.")
            site.clean_dest()

        for page in site.tree:
            page.parse()
            print(page.context.source_path)
        #     name = context.source_path.name
        #     context.validate_only = dry_run
        #
        #     modified = (context.is_modified or force or dry_run)
        #     if not modified:
        #         logger.debug("Found unmodified %s", name)
        #         continue
        #
        #     logger.info("Building page %s", name)
        #
        #     try:
        #         build_page(context)
        #     except (OSError, TemplateError, FileExistsError) as e:
        #         build_stats.errors += 1
        #         logger.exception("Failed to build", exc_info=e)
        #         continue
        #
        #     logger.info("Build OK")
        #     build_stats.add_stat(context.build_reason)
        #
        # if not (no_rss or dry_run):
        #     rss = site.make_rss()
        #     rss_path = site.dest_dir.joinpath("feed.xml")
        #
        #     rss_path.parent.mkdir(exist_ok=True)
        #     with rss_path.open("w") as out:
        #         out.write(rss)
        #
        # if not (no_sitemap or dry_run):
        #     sitemap = site.make_sitemap()
        #     sitemap_path = site.dest_dir.joinpath("sitemap.xml")
        #
        #     sitemap_path.parent.mkdir(exist_ok=True)
        #     with sitemap_path.open("w") as out:
        #         out.write(sitemap)

    logger.info(build_stats.summary())

if __name__ == "__main__":
    main()
