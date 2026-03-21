from nonebot_plugin_alconna import (
    Args,
    Option,
    Alconna,
    Arparma,
    MultiVar,
    CommandMeta,
    on_alconna,
)

from nonebot_plugin_fiqo.utils import (
    execute_tasks,
    global_formatter,
)
from nonebot_plugin_fiqo.services import fio_service

from .permissions import ADMIN

fiqo_uinfo = on_alconna(
    Alconna(
        "uinfo",
        Option("-un|--username", Args["username", str]),
        Option("-cc|--company-code", Args["company_code", str]),
        Option("-cn|--company-name", Args["company_name", MultiVar(str)]),
        meta=CommandMeta(
            description="[开发组] 查询用户或公司的信息",
        ),
    ),
    permission=ADMIN,
)


@fiqo_uinfo.handle()
async def _(param: Arparma) -> None:
    username: str | None = param.query[str]("username")
    company_code: str | None = param.query[str]("company_code")
    company_name: list[str] | None = param.query[list[str]]("company_name")
    company_name_str = " ".join(company_name) if company_name else None

    tasks = []
    if username:
        tasks.append(fio_service.get_user_and_company_info(username=username))
    if company_code:
        tasks.append(fio_service.get_user_and_company_info(company_code=company_code))
    if company_name_str:
        tasks.append(fio_service.get_user_and_company_info(company_name=company_name_str))
    if not tasks:
        await fiqo_uinfo.finish("请至少提供用户名、公司代码或公司名称中的一个")

    result = await execute_tasks(tasks)
    result.contents = list(set(result.contents))
    response = global_formatter.format_service_result(
        result,
        header="用户与公司查询结果：\n",
    )

    await fiqo_uinfo.finish(response)
