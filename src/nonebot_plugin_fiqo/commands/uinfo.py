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
    global_formatter,
)
from nonebot_plugin_fiqo.services import uinfo_service

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

    result = await uinfo_service.get_uinfo_results(
        username=username,
        company_code=company_code,
        company_name=company_name_str,
    )
    if not result.contents and not result.warnings:
        await fiqo_uinfo.finish("请至少提供用户名、公司代码或公司名称中的一个")
    response = global_formatter.format_service_result(
        result,
        header="用户与公司查询结果：\n",
    )

    await fiqo_uinfo.finish(response)
