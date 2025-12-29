import os, click, logging, time
from pathlib import Path
from .log import configure_logging
from .site import SiteRoot
from .build import build as build_page
from .exec import FileTypeError
from .cli import  BuildStats
from . import __version__

logger = logging.getLogger(__name__)
cwd = Path(os.getcwd())

@click.group()
@click.option('--verbose', '-v', is_flag=True, default=False)
@click.version_option(version=__version__)
def cli(verbose: bool) -> None:
    configure_logging(verbose)

@cli.command(help="Build the site.")
@click.option(
    '--force',
    help="Build all pages, even if unmodified",
    is_flag=True,
    default=False
)
@click.option(
    "--directory",
    default=cwd,
    type=Path,
    help="Use the specified directory, instead of the current directory"
)
def build(force: bool, directory: Path):
    logger.info("Building site at %s.\n", directory)
    s_time = time.perf_counter()
    site = SiteRoot(directory)
    build_stats = BuildStats()
    site.make_tree()

    logger.info("Found a total of %d pages.", len(site.tree))

    for context in site.tree:
        if not (context.is_modified or force):
            logger.debug(
                "%s has not been modified since last build. Use --force to overwrite anyway.",
                context.source_path.name
            )
            continue

        try:
            build_page(context)

        except OSError as e:
            build_stats.errors += 1
            logger.error(
                "Failed to build page %s: %s",
                context.source_path,
                "".join(e.args)
            )

        build_stats.add_stat(context.build_reason)

    e_time = time.perf_counter()
    build_stats.time_seconds = e_time - s_time

    logger.info(
        build_stats.summary(len(site.tree)),
    )

if __name__ == "__main__":
    cli()
