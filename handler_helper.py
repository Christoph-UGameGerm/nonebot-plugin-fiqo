import asyncio
from collections.abc import Awaitable, Callable

from nonebot import logger

from . import exception, model
from .fio_client import fio_service
from .msg_helper import MessageFormatHelper
from .weblate_term_provider import weblate_provider


async def handle_generic_query_batch(
    items: list[str],
    query_func: Callable[[str], Awaitable[model.QueryResult]],
    item_type_localized: str,
    helper: MessageFormatHelper
) -> None:
    """
    Generic handler for batch queries of items (e.g. materials, buildings).

     This function performs the following steps:
     1. Log the generic query request with a list of items to be queried.
     2. Executes the provided query function for each valid item concurrently.
     3. Collects and processes the results, identifying any errors.
     4. Constructs a response message based on the results and sends it.

     The query function should return a QueryResult object that contains
     either the successful result or an error type indicating what went wrong.

    :param items: List of items to query (e.g. material tickers, building tickers)
    :type items: list[str]
    :param query_func: Asynchronous function that takes an item to query\
        and returns a QueryResult indicating result and status.
    :type query_func: Callable[[str], Awaitable[model.QueryResult]]
    :param item_type_localized: Localized name of the item type for\
        constructing response messages (e.g. "材料", "建筑")
    :type item_type_localized: str
    :param helper: MessageFormatHelper instance for constructing the response message
    :type helper: MessageFormatHelper
    """
    logger.debug(f"Received query request for {item_type_localized}: {items}")

    query_tasks = [
        query_func(item)
        for item in items
    ]
    results = await asyncio.gather(*query_tasks)

    success_results = [r for r in results if r.error_type is None]
    if success_results:
        for result in success_results:
            helper.add_core(str(result.info))

    error_map: dict[model.QueryErrorType, list[str]] = {
        model.QueryErrorType.TICKER: [],
        model.QueryErrorType.NETWORK: [],
        model.QueryErrorType.I18N: []
    }

    for r in results:
        if r.error_type is not None:
            error_map[r.error_type].append(r.id)

    if error_map[model.QueryErrorType.TICKER]:
        helper.add_tail(f"错误的{item_type_localized}代码："
                        f"{', '.join(error_map[model.QueryErrorType.TICKER])}"
                        "，未找到相关信息。")
    if error_map[model.QueryErrorType.I18N]:
        helper.add_tail(f"获取{item_type_localized}信息的国际化内容时出现错误，"
                        f"涉及的{item_type_localized}代码："
                        f"{', '.join(error_map[model.QueryErrorType.I18N])}")
    if error_map[model.QueryErrorType.NETWORK]:
        helper.add_tail(f"连接查询{item_type_localized}信息时出现网络错误，"
                        f"涉及的{item_type_localized}代码："
                        f"{', '.join(error_map[model.QueryErrorType.NETWORK])}")

async def query_single_material(
    ticker: str,
    categories: model.FIOCategoriesResponse | None
) -> model.QueryResult:
    material_info: model.MaterialInfo | None = None
    try:
        fio_info = await fio_service.get_material_info(ticker)
        material_info = model.MaterialInfo(
            **fio_info.model_dump()
        )
        material_info.name = await weblate_provider.get_material_name(
            fio_info.name
        )
        material_info.desc = await weblate_provider.get_material_description(
            fio_info.name
        )
        if categories is not None:
            material_category_name = categories.get_category_name(fio_info.category)
            material_info.category = await weblate_provider.get_material_category(
                material_category_name)
        return model.QueryResult(
            id=ticker,
            info=material_info
        )
    except exception.WrongMaterialTickerError as e:
        logger.error(f"Wrong material ticker {ticker} error: {e}")
        return model.QueryResult(
            id=ticker,
            error_type=model.QueryErrorType.TICKER
        )
    except exception.BadConnectionError as e:
        logger.error(f"Bad connection error while fetching material {ticker}: {e}")
        return model.QueryResult(
            id=ticker,
            error_type=model.QueryErrorType.NETWORK
        )
    except exception.I18nFetchError as e:
        logger.error(f"I18n fetch error for material {ticker}: {e}")
        return model.QueryResult(
            id=ticker,
            info=material_info if material_info is not None else None,
            error_type=model.QueryErrorType.I18N
        )

async def query_single_building(
    ticker: str
) -> model.QueryResult:
    building_info: model.BuildingInfo | None = None
    try:
        fio_info = await fio_service.get_building_info(ticker)
        building_info = model.BuildingInfo(
            **fio_info.model_dump()
        )
        building_info.name = await weblate_provider.get_building_name(
            fio_info.name
        )
        building_info.desc = await weblate_provider.get_building_description(
            fio_info.name
        )
        building_info.expertise = await weblate_provider.get_expertise(
            fio_info.expertise
        )
        return model.QueryResult(
            id=ticker,
            info=building_info
        )
    except exception.WrongBuildingTickerError as e:
        logger.error(f"Wrong building ticker {ticker} error: {e}")
        return model.QueryResult(
            id=ticker,
            error_type=model.QueryErrorType.TICKER
        )
    except exception.BadConnectionError as e:
        logger.error(f"Bad connection error while fetching building {ticker}: {e}")
        return model.QueryResult(
            id=ticker,
            error_type=model.QueryErrorType.NETWORK
        )
    except exception.I18nFetchError as e:
        logger.error(f"I18n fetch error for building {ticker}: {e}")
        return model.QueryResult(
            id=ticker,
            info=building_info if building_info is not None else None,
            error_type=model.QueryErrorType.I18N
        )
