import re
import math
from datetime import timedelta
from collections import defaultdict

from nonebot import logger
from nonebot_plugin_alconna import UniMessage

from nonebot_plugin_fiqo import (
    exceptions as fiqo_exceptions,
)
from nonebot_plugin_fiqo.config import (
    FormatConfig,
    plugin_config,
)
from nonebot_plugin_fiqo.models import (
    CXOrder,
    PlanetDTO,
    RecipeDTO,
    BuildingDTO,
    MaterialDTO,
    FitResultDTO,
    BasePlanetDTO,
    CXMaterialDTO,
    ServiceResult,
    CoGCProgramDTO,
    CostMaterialDTO,
    FitRatioItemDTO,
    OfficePlanetDTO,
    FitRatioResultDTO,
    UserAndCompanyDTO,
)

PLANET_RESOURCE_TYPE_LABELS = {
    "GASEOUS": "气态",
    "LIQUID": "液态",
    "MINERAL": "固态",
}


class Formatter:
    def __init__(self, config: FormatConfig) -> None:
        self.config = config

    def clean_and_partition_group_nickname(self, nickname: str) -> list[str]:
        cleaned = re.sub(r"[(（][^|)）]*([|)）]|$)", "|", nickname)
        return [name.strip() for name in cleaned.split("|") if name.strip()]

    def format_timedelta(self, td: timedelta) -> str:
        total_seconds = int(abs(td.total_seconds()))
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days > 0:
            parts.append(f"{days}天")
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

    def _format_cx_order_list(
        self,
        data: list[CXOrder],
        currency: str,
        order_no: int,
        order_amount_field_width: int,
        order_price_field_width: int,
        *,
        reverse: bool = False,
    ) -> str:
        space_lead = " " * len(self.config.list_item_lead)
        orders = reversed(data[:order_no]) if reverse else data[:order_no]
        return "\n".join(
            [
                space_lead
                + f"{self._format_cx_order_amount(order):>{order_amount_field_width}}"
                + " @ "
                + f"{order.price:.2f} {currency}".rjust(order_price_field_width)
                + f" [{order.company_code}]"
                for order in orders
            ]
        )

    def format_cx_buy_order_list(
        self,
        data: list[CXOrder],
        currency: str,
        order_no: int,
        order_amount_field_width: int,
        order_price_field_width: int,
    ) -> str:
        return self._format_cx_order_list(
            data,
            currency,
            order_no,
            order_amount_field_width,
            order_price_field_width,
        )

    def format_cx_sell_order_list(
        self,
        data: list[CXOrder],
        currency: str,
        order_no: int,
        order_amount_field_width: int,
        order_price_field_width: int,
    ) -> str:
        return self._format_cx_order_list(
            data,
            currency,
            order_no,
            order_amount_field_width,
            order_price_field_width,
            reverse=True,
        )

    def format_building(self, data: BuildingDTO) -> str:
        workforce_lines = [
            (label, value)
            for label, value in [
                ("先驱者", data.pioneers),
                ("定居者", data.settlers),
                ("职技工", data.technicians),
                ("工程师", data.engineers),
                ("科学家", data.scientists),
            ]
            if value
        ]
        lines = [
            f"代码：{data.ticker}",
            f"名称：{data.name}",
            f"专精：{data.expertise or '无'}",
            *[f"{label}：{value}" for label, value in workforce_lines],
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

    def format_fit_result(self, data: FitResultDTO) -> str:
        lines = [
            f"最大装载量：{data.max_units}",
            f"剩余重量：{data.remaining_weight:.2f} t/吨",
            f"剩余体积：{data.remaining_volume:.2f} m³/立方米",
            f"限制因素：{data.limiting_factor}",
            f"单件重量：{data.unit_weight:.3f} t/吨",
            f"单件体积：{data.unit_volume:.3f} m³/立方米",
        ]
        if data.preset_key is not None:
            preset_display = (
                f"{data.preset_name} ({data.preset_key})"
                if data.preset_name
                else data.preset_key
            )
            preset_capacity = (
                f"{data.preset_weight:.0f}t/{data.preset_volume:.0f}m³"
                if data.preset_weight is not None and data.preset_volume is not None
                else "未知"
            )
            lines.append(f"运力预设：{preset_display} {preset_capacity}")
        return "\n".join(lines)

    def format_fitratio_result(self, data: FitRatioResultDTO) -> str:
        lines = [
            f"最大装载组数：{data.max_groups}",
            f"剩余重量：{data.remaining_weight:.2f} t/吨",
            f"剩余体积：{data.remaining_volume:.2f} m³/立方米",
            f"限制因素：{data.limiting_factor}",
            f"每组重量：{data.group_weight:.3f} t/吨",
            f"每组体积：{data.group_volume:.3f} m³/立方米",
            "材料组合：",
            self.format_fitratio_items(data.items),
        ]
        if data.preset_key is not None:
            preset_display = (
                f"{data.preset_name} ({data.preset_key})"
                if data.preset_name
                else data.preset_key
            )
            preset_capacity = (
                f"{data.preset_weight:.0f}t/{data.preset_volume:.0f}m³"
                if data.preset_weight is not None and data.preset_volume is not None
                else "未知"
            )
            lines.append(f"运力预设：{preset_display} {preset_capacity}")
        return "\n".join(lines)

    def format_fitratio_items(self, data: list[FitRatioItemDTO]) -> str:
        item_lead = self.config.list_item_lead
        return "\n".join([item_lead + f"{item.amount} {item.ticker}" for item in data])

    def format_cx_material(self, data: CXMaterialDTO, order_no: int) -> str:
        order_amount_field_width = max(
            len(self._format_cx_order_amount(order))
            for order in data.sell_orders + data.buy_orders
        )
        order_price_field_width = max(
            len(f"{order.price:.2f} {data.currency}")
            for order in data.sell_orders + data.buy_orders
        )
        update_td = data.time_since_update
        update_dir = "前" if update_td.total_seconds() >= 0 else "后"

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
            self.format_cx_sell_order_list(
                data.sell_orders,
                data.currency,
                order_no,
                order_amount_field_width,
                order_price_field_width,
            )
            if data.sell_orders
            else None,
            f"价差：{data.ask_price - data.bid_price:.2f} {data.currency}"
            if data.ask_price and data.bid_price
            else None,
            f"买单前{order_no}：" if data.buy_orders else None,
            self.format_cx_buy_order_list(
                data.buy_orders,
                data.currency,
                order_no,
                order_amount_field_width,
                order_price_field_width,
            )
            if data.buy_orders
            else None,
            f"更新时间：{self.format_timedelta(update_td)}{update_dir}",
        ]
        return "\n".join(filter(None, lines))

    def format_planet_name(self, natural_id: str, name: str) -> str:
        return natural_id + " - " + name if name != natural_id else natural_id

    def format_base_list(self, bases: list[BasePlanetDTO]) -> str:
        return "\n".join(
            self.config.list_item_lead
            + f"{self.format_planet_name(base.natural_id, base.name)}"
            for base in bases
        )

    def format_office_list(self, offices: list[OfficePlanetDTO]) -> str:
        return "\n".join(
            self.config.list_item_lead
            + f"{self.format_planet_name(office.natural_id, office.name)}"
            for office in offices
        )

    def format_user_company_info(self, data: UserAndCompanyDTO) -> str:
        lines = [
            f"用户名：{data.username}",
            f"订阅等级：{data.subscription_level}",
            f"公司名称：{data.company_name}",
            f"公司代码：{data.company_code}",
            f"集团名称：{data.corporation_name}" if data.corporation_name else None,
            f"集团代码：{data.corporation_code}" if data.corporation_code else None,
            f"公司评级：{data.rating}",
            f"创建天数：{data.created_days}",
            f"派系代码：{data.faction}",
            f"基地数量：{data.base_counts}",
            "基地列表：" if data.bases else None,
            self.format_base_list(data.bases) if data.bases else None,
            "在以下行星任管理者：" if data.offices else None,
            self.format_office_list(data.offices) if data.offices else None,
        ]
        return "\n".join(filter(None, lines))

    def format_user_company_key_info(self, data: UserAndCompanyDTO) -> str:
        lines = [
            f"用户名：{data.username}",
            f"公司名称：{data.company_name}",
            f"公司代码：{data.company_code}",
            f"派系代码：{data.faction}",
            f"订阅等级：{data.subscription_level}",
            f"创建天数：{data.created_days}",
        ]
        return "\n".join(lines)

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

    def format_planet_projects_list(self, data: PlanetDTO) -> str:
        item_lead = self.config.list_item_lead
        lines = [
            (item_lead + "行星监管中心") if data.has_adm else None,
            (item_lead + "全球商会") if data.has_cogc else None,
            (item_lead + "本地市场") if data.has_localmarket else None,
            (item_lead + "仓库") if data.has_warehouse else None,
        ]
        return "\n".join(filter(None, lines))

    def format_planet_resources_list(self, data: PlanetDTO) -> str:
        item_lead = self.config.list_item_lead
        lines = [
            (
                item_lead
                + f"{r.ticker} ({PLANET_RESOURCE_TYPE_LABELS.get(r.type, r.type)})"
                + f" - {r.daily_extraction:.2f}/天"
            )
            for r in data.resources
        ]
        return "\n".join(filter(None, lines))

    def format_cogc_program(self, program: CoGCProgramDTO) -> str:
        item_lead = self.config.list_item_lead
        program_name = program.type or "未知项目"
        if program.time_until_start.total_seconds() > 0:
            schedule_label = "开始"
            schedule_value = self.format_timedelta(program.time_until_start)
            schedule = f"{schedule_label}：{schedule_value}后"
        else:
            schedule_label = "剩余"
            schedule_value = self.format_timedelta(program.time_until_end)
            schedule = f"{schedule_label}：{schedule_value}"
        return item_lead + f"{program_name} ({schedule})"

    def format_planet(self, data: PlanetDTO) -> str:
        resources_block = (
            "\n" + self.format_planet_resources_list(data) if data.resources else "无"
        )
        projects_block = (
            "\n" + self.format_planet_projects_list(data)
            if any(
                [
                    data.has_adm,
                    data.has_cogc,
                    data.has_localmarket,
                    data.has_warehouse,
                ]
            )
            else "无"
        )
        lines = [
            f"编号：{data.natural_id}",
            "名称：" + (data.name if data.name else "无"),
            f"恒星系：{data.system_display_name}",
            "派系：" + (data.faction if data.faction else "无"),
            f"类型：{data.type_display}",
            f"肥沃度：{data.fertility_percent:.2f}%",
            f"重力：{data.gravity_display}",
            f"温度：{data.temperature_display}",
            f"压强：{data.pressure_display}",
            "资源：" + resources_block,
            "行星项目：" + projects_block,
            f"CoGC状态：{data.cogc_status}" if data.cogc_status else None,
            "CoGC项目：\n" + self.format_cogc_program(data.cogc_program)
            if data.cogc_program
            else None,
        ]
        return "\n".join(filter(None, lines))

    def format_warnings(self, warnings: list[Exception]) -> str:
        if not warnings:
            return ""

        grouped_warnings = defaultdict(list)
        for warning in warnings:
            logger.warning(
                f"Service returned warning: {warning=}\n"
                + f"Caused by: {type(warning.__cause__).__name__}: {warning.__cause__}"
            )
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
