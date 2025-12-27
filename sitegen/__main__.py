import os, click, logging, pathlib
from .log import configure_logging
from .site import SiteRoot
from .build import build as build_page

logger = logging.getLogger(__name__)
cwd = pathlib.Path(os.getcwd())


@click.group()
@click.option('--verbose', '-v', is_flag=True, default=False)
def cli(verbose: bool):
    configure_logging(verbose)


@cli.command(help="Build the site.")
@click.option('--force', help="Build all pages, even if unmodified", is_flag=True, default=False)
@click.option("--directory", default=cwd, help="Use the specified directory, instead of the current directory")
def build(force: bool, directory: str):
    """
    Build the site.
    :param force: Build all pages, even if unmodified.
    :param directory: Use the specified directory, instead of the current directory.
    :return: None
    """
    logger.info("Building site at %s.\n", directory)
    directory = pathlib.Path(directory)
    site = SiteRoot(directory)
    site.make_tree()
    total_found: int = len(site.tree)
    total_modified: int = 0
    total_new: int = 0

    logger.info("Found a total of %d pages.", total_found)

    for context in site.tree:
        source_lastmod: float = context.source_path.stat().st_mtime
        dest_lastmod: float = 0
        if context.dest_path.exists():
            dest_lastmod: float = context.dest_path.stat().st_mtime

        is_source_modified: bool = (source_lastmod < dest_lastmod)
        if is_source_modified and not force:
            logger.debug(
                "%s has not been modified since last build. Use --force to overwrite anyway.",
                context.source_path.name)
            total_found -= 1
            continue

        build_page(context)

        if dest_lastmod == 0:
            total_new += 1
        else:
            total_modified += 1

    logger.info(
        "\nSuccessfully built %d pages:" +
            "\n- %d new page(s)" +
            "\n- %d with change(s)" +
            "\n- %d unchanged",
        total_found,
        total_new,
        total_modified,
        len(site.tree) - (total_modified + total_new),
    )

if __name__ == "__main__":
    cli()
