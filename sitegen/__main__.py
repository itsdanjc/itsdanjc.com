import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Final
from jinja2 import TemplateError
from .log import configure_logging
from .site import SiteRoot
from .build import build as build_page
from .cli import  BuildStats
from . import __version__, __author__

CLI_HEADER_MSG: Final[str] = f"sitegen {__version__}, by {__author__}"
CLI_DESC: Final[str] = "Epilogue"

logger = logging.getLogger(__name__)
cwd = Path.cwd()

def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="cli", description=CLI_DESC)
    commands = parser.add_subparsers(title="commands", dest="commands", required=True)

    # Global Arguments
    parser.add_argument("-v", "--verbose", action="store_true", help="Show more info in logs")
    parser.add_argument("--version", action="version", version=__version__)

    # Build command
    build_cmd = commands.add_parser("build", help="Build the site.")
    build_cmd.add_argument(
        "-f","--force", action="store_true", help="Rebuild all pages.")
    build_cmd.add_argument(
        "-c","--clean", action="store_true", help="Clear the output directory, then build.")
    build_cmd.add_argument(
        "-d","--dry-run", action="store_true", help="Run as normal. but don't create build files.")
    build_cmd.add_argument(
        "-p", "--working-dir", type=Path, default=cwd,
        help="Use the specified directory, instead of the current directory")

    args = parser.parse_args(argv)
    print(CLI_HEADER_MSG, end="\n\n")
    configure_logging(args.verbose)
    try:
        match args.commands:
            case "build":
                build(args.force, args.working_dir, args.clean, args.dry_run)
            case _:
                parser.print_help()
    except KeyboardInterrupt:
        sys.exit(0)



def build(force: bool, directory: Path, perform_clean: bool, dry_run: bool) -> None:
    directory.resolve()
    logger.info("Building site at %s", directory)
    site = SiteRoot(directory)

    with BuildStats() as build_stats:
        for context in site.tree_iter():
            name = context.source_path.name

            if not (context.is_modified or force):
                logger.debug("Found unmodified %s", name)
                continue

            logger.info("Building page %s", name)

            try:
                build_page(context)
            except (OSError, TemplateError):
                build_stats.errors += 1
                logger.exception("Failed to build %s", name)
                continue

            logger.info("Build OK")
            build_stats.add_stat(context.build_reason)

    logger.info(build_stats.summary())

if __name__ == "__main__":
    main()
