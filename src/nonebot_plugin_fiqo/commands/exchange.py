from functools import partial

from arclet.alconna import MultiVar
from nonebot_plugin_alconna import (
    Alconna,
    Args,
    CommandMeta,
    Match,
    Option,
    Query,
    on_alconna,
    store_true,
)

from nonebot_plugin_fiqo.services import fio_service
from nonebot_plugin_fiqo.utils import (
    execute_batch,
    global_formatter,
)

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_exchange = on_alconna(
    Alconna(
        "cx",
        Args["ticker#交易所物品代码XXX.YYY", MultiVar(str)],
        Option(
            "-o|--orders",
            Args["orders#订单数量", int, 3],
            help_text="订单显示数量",
            action=store_true,
            default=False,
        ),
        meta=CommandMeta(
            description="[普通用户] 查询交易所物品信息",
            usage="/cx <ticker>",
            example="/cx RAT",
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)


@fiqo_exchange.handle()
async def _(
    ticker: Match[tuple[str, ...]], orders: Match[int]
) -> None:
    ticker_list = [t.strip().upper() for t in ticker.result]
    worker = partial(fio_service.get_exchange_material_info, order_no=orders.result)
    result = await execute_batch(ticker_list, worker)
    response = global_formatter.format_service_result(result, "交易所物品信息：\n")
    await fiqo_exchange.finish(response)
