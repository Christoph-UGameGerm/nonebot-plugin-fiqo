import asyncio
from collections.abc import Callable, Coroutine, Iterable
from typing import Any

from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.models import ServiceResult


async def execute_batch(
    items: Iterable[Any], worker: Callable[[Any], Coroutine[Any, Any, str]]
) -> ServiceResult:
    res = ServiceResult()

    tasks = [worker(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            res.warnings.append(result)
        elif isinstance(result, str):
            res.contents.append(result)
        else:
            res.contents.append(str(result))

    return res
