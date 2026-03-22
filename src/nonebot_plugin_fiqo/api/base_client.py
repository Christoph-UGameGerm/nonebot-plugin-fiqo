import json
import asyncio
from typing import Any, TypeVar

import httpx
from pydantic import TypeAdapter

from nonebot_plugin_fiqo.utils import disk_cache
from nonebot_plugin_fiqo.exceptions import (
    BadConnectionError,
    ResourceNotFoundError,
)

T = TypeVar("T")


class BaseClient:
    def __init__(self, base_url: str, timeout: int) -> None:
        self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._inflight: dict[str, asyncio.Task] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _freeze_params(self, params: dict | None) -> str | None:
        if not params:
            return None
        return json.dumps(params, sort_keys=True)

    def _get_unified_key(self, key: str, params: dict | None) -> str:
        safe_params = self._freeze_params(params)
        return f"{key}:{safe_params}" if safe_params else key

    def _get_lock(self, unified_key: str) -> asyncio.Lock:
        if unified_key not in self._locks:
            self._locks[unified_key] = asyncio.Lock()
        return self._locks[unified_key]

    async def _perform_request(
        self,
        endpoint: str,
        model: type[T] | Any,
        not_found_error: ResourceNotFoundError,
        params: dict | None = None,
    ) -> T:
        try:
            response = await self.client.get(endpoint, params=params)

            # HTTP-level "Not Found"
            # e.g. FIO returns 204, PrunPlanner return 404 on some endpoints
            if response.status_code in (204, 404):
                raise not_found_error

            response.raise_for_status()
            data = response.json()

            # Business-level "Not Found"
            # e.g. PrunPlanner returns []
            # e.g. Weblate returns {"count": 0, "results": []}
            if data == [] or (
                isinstance(data, dict) and "results" in data and not data["results"]
            ):
                raise not_found_error

            return TypeAdapter(model).validate_python(data)
        except httpx.RequestError as e:
            raise BadConnectionError(str(e)) from e

    async def request(
        self,
        key_and_model: tuple[str, type[T] | Any],
        endpoint: str,
        params: dict | None,
        not_found_error: ResourceNotFoundError,
        ttl: int | None = None,
    ) -> T:
        key, model = key_and_model
        unified_key = self._get_unified_key(key, params)

        if (ttl is not None) and (
            cache_entry := await disk_cache.get(unified_key, model)
        ):
            return cache_entry

        lock = self._get_lock(unified_key)
        async with lock:
            if (ttl is not None) and (
                cache_entry := await disk_cache.get(unified_key, model)
            ):
                return cache_entry

            if unified_key in self._inflight:
                task = self._inflight[unified_key]
                is_leader = False
            else:
                task = asyncio.create_task(
                    self._perform_request(
                        endpoint, model, not_found_error, params=params
                    )
                )
            self._inflight[unified_key] = task
            is_leader = True
        try:
            result = await task
            if is_leader and (ttl is not None):
                await disk_cache.set(unified_key, result, ttl)
            return result
        finally:
            if is_leader:
                self._inflight.pop(unified_key, None)
                self._locks.pop(unified_key, None)

    async def close(self) -> None:
        await self.client.aclose()
