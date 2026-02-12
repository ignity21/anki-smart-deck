import asyncio

from ankinote.utils.httpcli import close_session, init_session


class Application:
    def __init__(self):
        init_session()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # wait all pending tasks
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            _, still_pending = await asyncio.wait(pending, timeout=5)
            if still_pending:
                for t in still_pending:
                    t.cancel()
                await asyncio.gather(*still_pending, return_exceptions=True)

        await close_session()
