from nonebot import require

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")


from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import load_builtin_plugins as load_alconna_builtin_plugins

from nonebot_plugin_fiqo import commands as commands

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_FIQO",
    description="集成了 FIO 相关功能的 NoneBot 2 插件",
    usage="",
    type="application",
    config=Config,
)


load_alconna_builtin_plugins("help")
