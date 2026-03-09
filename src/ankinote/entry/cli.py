import click
from . import vocab
from rich.console import Console

console = Console(color_system="auto")


def print_banner():
    """Print welcome banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║        🎴  Anki AI-Powered Deck Generator  🎴           ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


@click.group()
def main():
    """Anki Smart Deck Generator CLI."""
    print_banner()


main.add_command(vocab.word)
