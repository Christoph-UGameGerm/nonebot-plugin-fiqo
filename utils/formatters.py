import datetime
import math
from collections import defaultdict
from datetime import timedelta

from nonebot_plugin_alconna import UniMessage

from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo import (
    exceptions as fiqo_exceptions,
)
from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.config import (
    FormatConfig,
    plugin_config,
)
from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.models import (
    BuildingDTO,
    CostMaterialDTO,
    CXMaterialDTO,
    CXOrder,
    MaterialDTO,
    RecipeDTO,
    ServiceResult,
)


class Formatter:
    def __init__(self, config: FormatConfig) -> None:
        self.config = config

    def format_timedelta(self, td: timedelta) -> str:
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分钟")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}秒")
        return " ".join(parts)

    def format_cost_material_list(self, data: list[CostMaterialDTO]) -> str:
        item_lead = self.config.list_item_lead
        return "\n".join([item_lead + f"{item.amount} {item.ticker}" for item in data])

    def format_recipe_list(self, data: list[RecipeDTO]) -> str:
        item_lead = self.config.list_item_lead
        space_lead = " " * len(item_lead)
        return "\n".join(
            [
                item_lead
                + f"{item.string_representation}\n"
                + space_lead
                + f"耗时: {self.format_timedelta(item.duration)}"
                for item in data
            ]
        )

    def _format_cx_order_amount(self, order: CXOrder) -> str:
        if order.amount == math.inf:
            return "∞"
        return str(int(order.amount))

    def format_cx_buy_order_list(
        self, data: list[CXOrder], currency: str, order_no: int
    ) -> str:
        space_lead = " " * len(self.config.list_item_lead)
        return "\n".join(
            [
                space_lead
                + f"{self._format_cx_order_amount(order):>{self.order_amount_field_width}}"  # noqa: E501
                + " @ "
                + f"{order.price:.2f} {currency}".rjust(self.order_price_field_width)
                for order in data[:order_no]
            ]
        )

    def format_cx_sell_order_list(
        self, data: list[CXOrder], currency: str, order_no: int
    ) -> str:
        space_lead = " " * len(self.config.list_item_lead)
        return "\n".join(
            [
                space_lead
                + f"{self._format_cx_order_amount(order):>{self.order_amount_field_width}}"  # noqa: E501
                + " @ "
                + f"{order.price:.2f} {currency}".rjust(self.order_price_field_width)
                for order in reversed(data[:order_no])
            ]
        )

    def format_building(self, data: BuildingDTO) -> str:
        lines = [
            f"代码：{data.ticker}",
            f"名称：{data.name}",
            f"专精：{data.expertise or '无'}",
            f"先驱者：{data.pioneers}" if data.pioneers else None,
            f"定居者：{data.settlers}" if data.settlers else None,
            f"职技工：{data.technicians}" if data.technicians else None,
            f"工程师：{data.engineers}" if data.engineers else None,
            f"科学家：{data.scientists}" if data.scientists else None,
            f"占地面积：{data.area}",
            "建造材料：" if data.cost else None,
            self.format_cost_material_list(data.cost) if data.cost else None,
            "可用配方：" if data.recipes else None,
            self.format_recipe_list(data.recipes) if data.recipes else None,
            f"描述：{data.desc or '无'}",
        ]
        return "\n".join(filter(None, lines))

    def format_material(self, data: MaterialDTO) -> str:
        lines = [
            f"代码：{data.ticker}",
            f"名称：{data.name}",
            f"类别：{data.category}",
            f"重量：{data.weight} t/吨",
            f"体积：{data.volume} m³/立方米",
            f"描述：{data.desc or '无'}",
        ]
        return "\n".join(lines)

    def format_cx_material(self, data: CXMaterialDTO, order_no: int) -> str:
        self.order_amount_field_width = max(
            len(self._format_cx_order_amount(order))
            for order in data.sell_orders + data.buy_orders
        )
        self.order_price_field_width = max(
            len(f"{order.price:.2f} {data.currency}")
            for order in data.sell_orders + data.buy_orders
        )

        lines = [
            f"代码：{data.ticker}",
            f"交易所：{data.exchange}",
            f"货币：{data.currency}",
            f"价格：{data.price:.2f} {data.currency}",
            f"卖价：{data.ask_price:.2f} {data.currency} " + f"({data.ask_size})",
            f"买价：{data.bid_price:.2f} {data.currency} " + f"({data.bid_size})",
            f"供应量：{data.supply}",
            f"需求量：{data.demand}",
            f"系统做市卖价：{data.MM_sell:.2f} {data.currency}"
            if data.MM_sell is not None
            else None,
            f"系统做市买价：{data.MM_buy:.2f} {data.currency}"
            if data.MM_buy is not None
            else None,
            f"交易量：{data.traded} (24H)",
            f"卖单前{order_no}：" if data.sell_orders else None,
            self.format_cx_sell_order_list(data.sell_orders, data.currency, order_no)
            if data.sell_orders
            else None,
            f"价差：{data.ask_price - data.bid_price:.2f} {data.currency}"
            if data.ask_price and data.bid_price
            else None,
            f"买单前{order_no}：" if data.buy_orders else None,
            self.format_cx_buy_order_list(data.buy_orders, data.currency, order_no)
            if data.buy_orders
            else None,
            "更新时间："
            + self.format_timedelta(
                datetime.datetime.now(datetime.UTC) - data.timestamp
            )
            + "前",
        ]
        return "\n".join(filter(None, lines))

    def format_service_result(
        self, result: ServiceResult, header: str, sep: str = "\n\n"
    ) -> UniMessage:
        formatted_contents = UniMessage()
        if result.contents:
            formatted_contents = UniMessage(header + sep.join(result.contents))
            if result.warnings:
                formatted_contents += sep
        if result.warnings:
            formatted_contents += self.format_warnings(result.warnings)
        return formatted_contents

    def format_warnings(self, warnings: list[Exception]) -> str:
        if not warnings:
            return ""

        grouped_warnings = defaultdict(list)
        for warning in warnings:
            grouped_warnings[type(warning)].append(warning)

        warning_summary = ["存在以下问题："]
        for warning_type, warning_list in grouped_warnings.items():
            if issubclass(warning_type, fiqo_exceptions.ResourceNotFoundError):
                tickers = [w.identifier for w in warning_list]
                warning_summary.append(
                    f"错误的{warning_list[0].resource_type}：{', '.join(tickers)}"
                )
            elif issubclass(warning_type, fiqo_exceptions.EvaluationError):
                messages = [w.err_message for w in warning_list]
                warning_summary.append(f"计算错误：{', '.join(messages)}")
            elif warning_type is fiqo_exceptions.BadConnectionError:
                warning_summary.append("网络连接异常，请稍后再试")
            else:
                warning_summary.append(
                    f"{warning_type.__name__}："
                    + "\n".join(str(w) for w in warning_list)
                )
        return "\n".join(warning_summary)


global_formatter = Formatter(plugin_config.format)
