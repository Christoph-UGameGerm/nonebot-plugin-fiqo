import hashlib
import json
import time
from typing import Generic, TypeVar

import anyio
import nonebot_plugin_localstore as localstore
from nonebot import logger
from pydantic import BaseModel, TypeAdapter, ValidationError

T = TypeVar("T", bound=BaseModel)


class CacheItem(BaseModel, Generic[T]):
    data: T
    expire_at: float


class DiskCacheManager:
    def __init__(self) -> None:
        self.base_path = anyio.Path(localstore.get_plugin_cache_dir())

    async def _init_dir(self) -> None:
        await self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, cache_key: str) -> anyio.Path:
        hashed_id = hashlib.md5(cache_key.encode("utf-8")).hexdigest()
        return self.base_path / f"{hashed_id}.json"

    async def set(self, cache_key: str, data: BaseModel, ttl: int) -> None:
        await self._init_dir()
        file_path = self._get_file_path(cache_key)
        cache_item = CacheItem[type(data)](data=data, expire_at=time.time() + ttl)
        try:
            json_str = cache_item.model_dump_json(by_alias=True)
            await file_path.write_text(json_str, encoding="utf-8")
            logger.debug(
                f"Disk cache set for key '{cache_key}' with TTL {ttl} seconds."
            )
        except (OSError, TypeError, ValueError) as e:
            logger.error(f"Error writing cache file for key '{cache_key}': {e}")

    async def get(self, cache_key: str, data_type: type[T]) -> T | None:
        file_path = self._get_file_path(cache_key)
        if not await file_path.exists():
            return None

        try:
            json_content = await file_path.read_text(encoding="utf-8")
            adapter = TypeAdapter(CacheItem[data_type])
            cache_item = adapter.validate_json(json_content)
            logger.debug(
                f"Cache file read successfully for {data_type.__name__}\n {cache_item=}"
            )
        except (
            FileNotFoundError,
            PermissionError,
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
            TypeError,
            ValidationError,
        ) as e:
            logger.warning(
                f"Error reading cache file for {data_type.__name__}"
                f" cache key '{cache_key}': {e}."
                f" Treating as cache miss and clearing cache file."
            )
            # Treat any exception as a cache miss.
            # Clear the cache file.
            await file_path.unlink(missing_ok=True)
            return None

        if cache_item.expire_at < time.time():
            logger.info(
                f"Cache expired for {data_type.__name__}, cache key '{cache_key}'."
            )
            await file_path.unlink(missing_ok=True)
            return None

        logger.debug(f"Cache hit for {data_type.__name__} cache key '{cache_key}'.")
        return cache_item.data

    async def clear_all(self) -> None:
        if not await self.base_path.exists():
            logger.debug("Cache directory does not exist, nothing to clear.")
            return
        count = 0
        try:
            async for file_path in self.base_path.iterdir():
                if await file_path.is_file() and file_path.suffix == ".json":
                    await file_path.unlink()
                    count += 1
            logger.info(f"Cleared {count} cache files from disk cache.")
        except OSError as e:
            logger.error(f"Error clearing disk cache: {e}")


disk_cache = DiskCacheManager()
