import sys

import click
from loguru import logger

from .phrase import phrase
from .sentence import sentence
from .word import word


@click.group()
@click.version_option()
def cli():
    """Anki card generator"""
    pass


cli.add_command(word)
cli.add_command(phrase)
cli.add_command(sentence)


def main():
    logger.remove()  # Remove default logger
    logger.add(
        sys.stderr,
        colorize=True,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    )
    cli()
