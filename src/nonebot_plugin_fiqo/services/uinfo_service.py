import asyncio
from typing import Literal

from nonebot_plugin_fiqo.utils import execute_tasks, global_formatter
from nonebot_plugin_fiqo.models import ServiceResult

from .game_info_service import info_service


class UinfoService:
    @staticmethod
    async def resolve_lookup_token_from_nickname(
        nickname: str,
        target: Literal["company_code", "username"],
    ) -> str | None:
        normalized_nickname = nickname.replace("丨", " | ")
        nickname_fields = global_formatter.clean_and_partition_group_nickname(
            normalized_nickname
        )
        if not nickname_fields:
            return None

        results = await asyncio.gather(
            *[
                info_service.identify_user_company_token(field, index)
                for index, field in enumerate(nickname_fields)
            ]
        )

        target_label = "公司代码" if target == "company_code" else "用户名"
        for _, matches in results:
            for label, dto in matches:
                if label != target_label or dto is None:
                    continue
                return dto.company_code if target == "company_code" else dto.username
        return None

    @staticmethod
    async def resolve_company_code_from_nickname(nickname: str) -> str | None:
        return await UinfoService.resolve_lookup_token_from_nickname(
            nickname, "company_code"
        )

    @staticmethod
    async def resolve_username_from_nickname(nickname: str) -> str | None:
        return await UinfoService.resolve_lookup_token_from_nickname(
            nickname, "username"
        )

    @staticmethod
    async def get_uinfo_results(
        username: str | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> ServiceResult:
        tasks = []
        if username:
            tasks.append(info_service.get_user_and_company_info(username=username))
        if company_code:
            tasks.append(
                info_service.get_user_and_company_info(company_code=company_code)
            )
        if company_name:
            tasks.append(
                info_service.get_user_and_company_info(company_name=company_name)
            )

        if not tasks:
            return ServiceResult()

        result = await execute_tasks(tasks)
        result.contents = list(set(result.contents))
        return result


uinfo_service = UinfoService()
