import click, logging
from .log import configure_logging

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, default=False)
def cli(verbose: bool):
    configure_logging(verbose)


@cli.command(help="Build the site.")
def build():
    logger.info("Hello world")


if __name__ == "__main__":
    cli()
