import click

from .word import word


@click.group()
@click.version_option()
def cli():
    """Anki card generator"""
    pass


cli.add_command(word)


def main():
    cli()
