from nonebot_plugin_fiqo.utils import execute_tasks
from nonebot_plugin_fiqo.models import ServiceResult

from .game_info_service import info_service


class UinfoService:
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
