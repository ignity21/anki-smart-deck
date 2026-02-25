import click


@click.group()
def word():
    """Word related commands."""
    pass

@word.command()
def create_note_type():
    """Create Anki note type for words."""
