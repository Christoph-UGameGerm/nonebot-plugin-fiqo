import functools
from collections.abc import Callable
from typing import Any

from arclet.alconna import Arparma
from nonebot.log import logger
from nonebot.matcher import current_matcher

from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.exceptions import (
    FIQOBaseError,
)


def handle_log_and_err() -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try to extract command context if available
            matcher = current_matcher.get()
            arparma_result = kwargs.get("result")
            cmd_name = func.__name__
            if isinstance(arparma_result, Arparma):
                cmd_name = "/" + arparma_result.source.command

            # Log the start of command execution
            logger.debug(
                f"Handling: {cmd_name}\nMatcher: {matcher=}\nParams: {args=}, {kwargs=}"
            )

            try:
                # Execute the function
                await func(*args, **kwargs)

                # Log the end of command execution
                logger.debug(f"Finished: {cmd_name}")

            # Fatal Error Handling
            except FIQOBaseError as e:
                logger.error(f"Error intercepting {cmd_name}: {e}")
                await matcher.finish("发生未知的FIQO业务报错，请联系管理员。")

        return wrapper

    return decorator
