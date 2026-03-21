import asyncio
from collections.abc import Callable, Coroutine, Iterable
from typing import Any, TypeVar

from pydantic import BaseModel

from nonebot_plugin_fiqo.models import ServiceResult

T = TypeVar("T", bound=BaseModel)

async def execute_batch(
    items: Iterable[Any], worker: Callable[[Any], Coroutine[Any, Any, str]]
) -> ServiceResult:
    tasks = [worker(item) for item in items]

    return await execute_tasks(tasks)


async def execute_tasks(tasks: Iterable[Coroutine[Any, Any, str]]) -> ServiceResult:
    res = ServiceResult()

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            res.warnings.append(result)
        elif isinstance(result, str):
            res.contents.append(result)
        else:
            res.contents.append(str(result))

    return res
