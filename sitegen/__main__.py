import os, click, logging, time
from pathlib import Path
from jinja2 import TemplateError
from .log import configure_logging
from .site import SiteRoot
from .build import build as build_page
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
    logger.info("Building site at %s.", directory)
    s_time = time.perf_counter()
    site = SiteRoot(directory)
    build_stats = BuildStats()
    site.make_tree()
    i, m = 0, len(site.tree)
    logger.info("Building %d pages...", len(site.tree))

    for context in site.tree:
        i += 1
        if not (context.is_modified or force):
            logger.debug("%s not modified.",context.source_path.name)
            continue

        try:
            logger.info("[%d/%d] %s.",i, m, context.source_path.name)
            build_page(context)

        except (OSError, TemplateError) as e:
            build_stats.errors += 1
            logger.error("%s: %s",context.source_path.name, "".join(e.args))

        build_stats.add_stat(context.build_reason)

    e_time = time.perf_counter()
    build_stats.time_seconds = e_time - s_time

    logger.info(build_stats.summary(m))

if __name__ == "__main__":
    cli()
