import re
import asyncio
from collections import OrderedDict

from nonebot_plugin_fiqo.api import fio_client
from nonebot_plugin_fiqo.utils import execute_tasks, global_formatter
from nonebot_plugin_fiqo.config import plugin_config
from nonebot_plugin_fiqo.models import ServiceResult, FitRatioItemDTO
from nonebot_plugin_fiqo.exceptions import EvaluationError, WrongCargoPresetError

from .math_service import math_service

CAPACITY_TOKEN_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>[tTmM])$")
COMPACT_RATIO_TOKEN_PATTERN = re.compile(
    r"^(?P<amount>\d+)?(?P<ticker>[A-Za-z][A-Za-z0-9]*)$"
)
INTEGER_TOKEN_PATTERN = re.compile(r"^\d+$")


class FitService:
    @staticmethod
    def _is_preset_key(token: str) -> bool:
        normalized_key = token.upper()
        return any(
            key.upper() == normalized_key for key in plugin_config.game.cargo_presets
        )

    @staticmethod
    def _resolve_preset(
        preset_key: str,
    ) -> tuple[str, float, float, str | None]:
        normalized_key = preset_key.upper()
        for key, preset in plugin_config.game.cargo_presets.items():
            if key.upper() == normalized_key:
                return key, preset.weight, preset.volume, preset.display_name
        raise WrongCargoPresetError(preset_key)

    @staticmethod
    def _parse_capacity_token(token: str) -> tuple[str, float]:
        matched = CAPACITY_TOKEN_PATTERN.fullmatch(token)
        if matched is None:
            raise EvaluationError(f"无效的载荷参数: {token}")
        value = float(matched.group("value"))
        unit = matched.group("unit").lower()
        kind = "weight" if unit == "t" else "volume"
        return kind, value

    @staticmethod
    def resolve_fit_inputs(
        capacity_1: str | None,
        capacity_2: str | None,
        ship_preset: str | None,
    ) -> tuple[float, float, str | None, str | None, float | None, float | None]:
        capacity_tokens = [
            token.strip()
            for token in [capacity_1, capacity_2]
            if token is not None and token.strip()
        ]
        return FitService.resolve_capacity_inputs(capacity_tokens, ship_preset)

    @staticmethod
    def resolve_capacity_inputs(
        capacity_tokens: list[str],
        ship_preset: str | None,
    ) -> tuple[float, float, str | None, str | None, float | None, float | None]:
        normalized_capacity_tokens = [
            token.strip() for token in capacity_tokens if token.strip()
        ]

        if ship_preset is not None and ship_preset.strip():
            if normalized_capacity_tokens:
                raise EvaluationError("运力预设不能与显式重量/体积参数混用")
            preset_key, weight, volume, display_name = FitService._resolve_preset(
                ship_preset.strip()
            )
            return weight, volume, preset_key, display_name, weight, volume

        if not normalized_capacity_tokens:
            raise EvaluationError("缺少载荷参数")

        if (
            len(normalized_capacity_tokens) == 1
            and CAPACITY_TOKEN_PATTERN.fullmatch(normalized_capacity_tokens[0]) is None
        ):
            preset_key, weight, volume, display_name = FitService._resolve_preset(
                normalized_capacity_tokens[0]
            )
            return weight, volume, preset_key, display_name, weight, volume

        if len(normalized_capacity_tokens) != 2:
            raise EvaluationError("请提供一组重量和体积，或提供一个运力预设")

        parsed_tokens = [
            FitService._parse_capacity_token(token)
            for token in normalized_capacity_tokens
        ]
        capacities = dict(parsed_tokens)
        if len(capacities) != 2:
            raise EvaluationError("重量和体积参数必须各提供一次")
        return capacities["weight"], capacities["volume"], None, None, None, None

    @staticmethod
    def resolve_fitratio_inputs(
        tokens: list[str],
        ship_preset: str | None,
    ) -> tuple[
        list[tuple[str, int]],
        float,
        float,
        str | None,
        str | None,
        float | None,
        float | None,
    ]:
        normalized_tokens = [
            token.strip() for token in tokens if token and token.strip()
        ]
        if not normalized_tokens:
            raise EvaluationError("请至少提供一组材料组合和载荷参数")

        ratio_tokens = normalized_tokens
        capacity_tokens: list[str] = []

        if ship_preset is not None and any(
            CAPACITY_TOKEN_PATTERN.fullmatch(token) is not None
            for token in normalized_tokens
        ):
            raise EvaluationError("运力预设不能与显式重量/体积参数混用")

        if ship_preset is None and len(normalized_tokens) >= 1:
            maybe_preset = normalized_tokens[-1]
            if (
                FitService._is_preset_key(maybe_preset)
                and CAPACITY_TOKEN_PATTERN.fullmatch(maybe_preset) is None
            ):
                ship_preset = maybe_preset
                ratio_tokens = normalized_tokens[:-1]
            elif len(normalized_tokens) >= 2 and all(
                CAPACITY_TOKEN_PATTERN.fullmatch(token) is not None
                for token in normalized_tokens[-2:]
            ):
                capacity_tokens = normalized_tokens[-2:]
                ratio_tokens = normalized_tokens[:-2]

        if ship_preset is not None and ship_preset.strip():
            capacity = FitService.resolve_capacity_inputs([], ship_preset)
        else:
            if not capacity_tokens:
                raise EvaluationError("请提供一组重量和体积，或提供一个运力预设")
            capacity = FitService.resolve_capacity_inputs(capacity_tokens, None)

        if not ratio_tokens:
            raise EvaluationError("请至少提供一种材料")

        materials = FitService._parse_fitratio_materials(ratio_tokens)
        return (materials, *capacity)

    @staticmethod
    def _parse_fitratio_materials(tokens: list[str]) -> list[tuple[str, int]]:
        merged: OrderedDict[str, int] = OrderedDict()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if INTEGER_TOKEN_PATTERN.fullmatch(token):
                amount = int(token)
                if amount <= 0:
                    raise EvaluationError(f"无效的材料数量: {token}")
                if i + 1 >= len(tokens):
                    raise EvaluationError(f"数量 {token} 后缺少材料代码")
                ticker = tokens[i + 1].strip().upper()
                if not COMPACT_RATIO_TOKEN_PATTERN.fullmatch(ticker):
                    raise EvaluationError(f"无效的材料代码: {tokens[i + 1]}")
                merged[ticker] = merged.get(ticker, 0) + amount
                i += 2
                continue

            matched = COMPACT_RATIO_TOKEN_PATTERN.fullmatch(token)
            if matched is None:
                raise EvaluationError(f"无效的材料组合参数: {token}")

            amount_raw = matched.group("amount")
            ticker = matched.group("ticker").upper()
            amount = int(amount_raw) if amount_raw is not None else 1
            if amount <= 0:
                raise EvaluationError(f"无效的材料数量: {token}")
            merged[ticker] = merged.get(ticker, 0) + amount
            i += 1

        return list(merged.items())

    @staticmethod
    async def get_fit_info(
        ticker: str,
        max_weight: float,
        max_volume: float,
        preset_key: str | None = None,
        preset_name: str | None = None,
        preset_weight: float | None = None,
        preset_volume: float | None = None,
    ) -> str:
        if not ticker.strip():
            raise EvaluationError("请至少提供材料代码和一组载荷参数")

        ticker = ticker.strip().upper()
        material = await fio_client.get_material_info(ticker)
        result = math_service.calculate_fit(
            material,
            max_weight=max_weight,
            max_volume=max_volume,
            preset_key=preset_key,
            preset_name=preset_name,
            preset_weight=preset_weight,
            preset_volume=preset_volume,
        )
        return global_formatter.format_fit_result(result)

    @staticmethod
    async def get_fit_result(
        ticker: str | None,
        capacity_1: str | None = None,
        capacity_2: str | None = None,
        ship_preset: str | None = None,
    ) -> ServiceResult:
        if ticker is None:
            return ServiceResult(
                warnings=[EvaluationError("请至少提供材料代码和一组载荷参数")]
            )

        try:
            (
                max_weight,
                max_volume,
                preset_key,
                preset_name,
                preset_weight,
                preset_volume,
            ) = FitService.resolve_fit_inputs(capacity_1, capacity_2, ship_preset)
        except Exception as e:
            return ServiceResult(warnings=[e])

        return await execute_tasks(
            [
                FitService.get_fit_info(
                    ticker=ticker,
                    max_weight=max_weight,
                    max_volume=max_volume,
                    preset_key=preset_key,
                    preset_name=preset_name,
                    preset_weight=preset_weight,
                    preset_volume=preset_volume,
                )
            ]
        )

    @staticmethod
    async def get_fitratio_info(
        materials: list[tuple[str, int]],
        max_weight: float,
        max_volume: float,
        preset_key: str | None = None,
        preset_name: str | None = None,
        preset_weight: float | None = None,
        preset_volume: float | None = None,
    ) -> str:
        material_infos = await asyncio.gather(
            *[fio_client.get_material_info(ticker) for ticker, _ in materials]
        )
        items: list[FitRatioItemDTO] = []
        for (ticker, amount), material in zip(materials, material_infos, strict=True):
            if material.weight <= 0 or material.volume <= 0:
                raise EvaluationError(f"材料 {ticker} 重量或体积异常，无法计算装载数量")
            items.append(
                FitRatioItemDTO(
                    ticker=ticker,
                    amount=amount,
                    unit_weight=material.weight,
                    unit_volume=material.volume,
                    total_weight=material.weight * amount,
                    total_volume=material.volume * amount,
                )
            )

        result = math_service.calculate_fitratio(
            items,
            max_weight=max_weight,
            max_volume=max_volume,
            preset_key=preset_key,
            preset_name=preset_name,
            preset_weight=preset_weight,
            preset_volume=preset_volume,
        )
        return global_formatter.format_fitratio_result(result)

    @staticmethod
    async def get_fitratio_result(
        tokens: list[str],
        ship_preset: str | None = None,
    ) -> ServiceResult:
        try:
            (
                materials,
                max_weight,
                max_volume,
                preset_key,
                preset_name,
                preset_weight,
                preset_volume,
            ) = FitService.resolve_fitratio_inputs(tokens, ship_preset)
        except Exception as e:
            return ServiceResult(warnings=[e])

        return await execute_tasks(
            [
                FitService.get_fitratio_info(
                    materials=materials,
                    max_weight=max_weight,
                    max_volume=max_volume,
                    preset_key=preset_key,
                    preset_name=preset_name,
                    preset_weight=preset_weight,
                    preset_volume=preset_volume,
                )
            ]
        )


fit_service = FitService()
