import sys

# import aiohttp
import click

# import litellm
# from litellm.llms.custom_httpx.aiohttp_handler import BaseLLMAIOHTTPHandler
from loguru import logger

from .phrase import phrase
from .sentence import sentence
from .word import word

# session = aiohttp.ClientSession(
#     timeout=aiohttp.ClientTimeout(total=60),
#     connector=aiohttp.TCPConnector(
#         limit=10,
#         limit_per_host=5,
#         enable_cleanup_closed=True,
#     ),
# )


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
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
    )
    # litellm.base_llm_aiohttp_handler = BaseLLMAIOHTTPHandler(client_session=session)
    cli()
