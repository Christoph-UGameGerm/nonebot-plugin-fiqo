import hashlib
import json
import time
from pathlib import Path
from typing import Generic, Optional, TypeVar

import nonebot_plugin_localstore as localstore
from nonebot import logger
from pydantic import BaseModel, TypeAdapter, ValidationError

T = TypeVar("T", bound=BaseModel)

class CacheItem(BaseModel, Generic[T]):
    data: T
    expire_at: float

class CacheManager:
    """
    Cache manager for caching pydantic model data with expiration support.
    Cache files are stored in the plugin's cache directory with a hashed filename
    The hashed id is based on the combination of the data type and ticker
    to ensure uniqueness.
    """

    base_path: Path = localstore.get_plugin_cache_dir()

    def _get_file_path(self, data_type: type[T], ticker: str) -> Path:
        """
        Get the file path for the cache file based on data type and ticker.

        :param data_type: Type of the data object to be cached
        :type data_type: type[T]
        :param ticker: Unique identifier for the object
        :type ticker: str
        :return: Pathlib Path to the cache file
        :rtype: Path
        """
        identifier = f"{data_type.__name__}_{ticker}"
        hashed_id = hashlib.md5(identifier.encode("utf-8")).hexdigest()
        logger.debug(f"Hash id for cache: {hashed_id},"
                     f" Data type: {data_type.__name__},"
                     f" ticker: '{ticker}'")
        return self.base_path / f"{hashed_id}.json"

    def set(self, data: BaseModel, ticker: str, expire_in: int=2419200) -> None:
        """
        Set cache data for object with a specific ticker with an expiration time.

        :param data: The data object to be cached
        :type data: object
        :param ticker: The unique identifier for the cache entry
        :type ticker: str
        :param expire_in: Time in seconds until the cache expires,
        default is 28 days (2419200 seconds)
        :type expire_in: int
        """
        file_path = self._get_file_path(type(data), ticker)
        cache_item = CacheItem[type(data)](
            data=data,
            expire_at=time.time() + expire_in
        )
        file_path.write_text(cache_item.model_dump_json(by_alias=True),
                             encoding="utf-8")
        logger.info(f"Cache set for {type(data).__name__},"
                    f" ticker: '{ticker}'. Cache file path: {file_path},"
                    f" expires in {expire_in} seconds.")

    def get(self, data_type: type[T], ticker: str) -> Optional[T]:
        """
        Get cached data for an object with a specific ticker \
            if it exists and is not expired.

        :param data_type: The type of the data object to be retrieved from cache
        :type data_type: type[T]
        :param ticker: The unique identifier for the cached object
        :type ticker: str
        :return: The cached data object if found and not expired, otherwise None
        :rtype: T | None
        """
        file_path = self._get_file_path(data_type, ticker)
        if not file_path.exists():
            logger.info(f"Cache miss for {data_type.__name__},"
                        f" ticker '{ticker}'."
                        f" Cache file does not exist.")
            return None

        try:
            json_content = file_path.read_text(encoding="utf-8")
            adapter = TypeAdapter(CacheItem[data_type])
            cache_item = adapter.validate_json(json_content)
            logger.debug(f"Cache file read successfully for {data_type.__name__},"
                         f" ticker '{ticker}'."
                         f" Cache item: {cache_item}")
        except (FileNotFoundError, PermissionError, OSError, UnicodeDecodeError,
                json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
            logger.error(f"Error reading cache file for {data_type.__name__}"
                         f" ticker '{ticker}': {e}."
                         f" Treating as cache miss and clearing cache file.")
            # Treat any exception as a cache miss.
            # Clear the cache file.
            file_path.unlink(missing_ok=True)
            return None

        if cache_item.expire_at < time.time():
            logger.info(f"Cache expired for {data_type.__name__},"
                        f" ticker '{ticker}'.")
            file_path.unlink(missing_ok=True)
            return None

        logger.debug(f"Cache hit for {data_type.__name__}"
                     f" ticker '{ticker}'")
        return cache_item.data

cache_manager = CacheManager()
