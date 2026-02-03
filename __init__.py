from arclet.alconna import Alconna, Args, MultiVar, StrMulti
from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import CommandMeta, Match, on_alconna

from .config import Config
from .resources import Models, Replys

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_FIQO",
    description="集成了 FIO 相关功能的 NoneBot 2 插件",
    usage="",
    type="application",
    config=Config,
)

plugin_config = get_plugin_config(Config)

# Responders
"""
Lorem 命令
生成随机的占位文字
基本仅用于测试目的
"""
fiqo_lorem = on_alconna(
    Alconna(
        "lorem",
        meta=CommandMeta(
            description="生成随机的占位文字",
        )
    )
)

@fiqo_lorem.handle()
async def handle_fiqo_lorem() -> None:
    await fiqo_lorem.finish(Replys.LOREM)
