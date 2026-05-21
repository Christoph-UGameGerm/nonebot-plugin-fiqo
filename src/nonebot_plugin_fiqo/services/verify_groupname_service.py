import asyncio

from nonebot_plugin_fiqo.utils import (
    global_formatter,
    analyze_nickname_entities,
)

from .game_info_service import info_service


class VerifyGroupnameService:
    @staticmethod
    async def get_verification_report(nickname: str) -> str:
        normalized_nickname = nickname
        symbol_warning = "丨" in normalized_nickname
        if symbol_warning:
            normalized_nickname = normalized_nickname.replace("丨", " | ")

        nickname_fields = global_formatter.clean_and_partition_group_nickname(
            normalized_nickname
        )
        tasks = [
            info_service.identify_user_company_token(field, index)
            for index, field in enumerate(nickname_fields)
        ]
        service_result = await asyncio.gather(*tasks)

        best_dto, report_lines = analyze_nickname_entities(service_result)

        warning_header = (
            "分隔符警告：昵称中包含 '丨'，建议使用两侧带空格的 '|' 作为分隔符。\n"
            if symbol_warning
            else ""
        )
        if best_dto is None:
            return warning_header + "暂无置信度足够的游戏内用户或公司信息"

        return (
            warning_header
            + "\n".join(report_lines)
            + "\n"
            + global_formatter.format_user_company_key_info(best_dto)
        )


verify_groupname_service = VerifyGroupnameService()
