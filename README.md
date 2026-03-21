<div align="center">
    <a href="https://v2.nonebot.dev/store">
    <img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-template/refs/heads/resource/.docs/NoneBotPlugin.svg" width="310" alt="logo"></a>

## ✨ nonebot-plugin-fiqo ✨
[![LICENSE](https://img.shields.io/github/license/Christoph-UGameGerm/nonebot-plugin-fiqo.svg)](./LICENSE)
[![pypi](https://img.shields.io/pypi/v/nonebot-plugin-fiqo.svg)](https://pypi.python.org/pypi/nonebot-plugin-fiqo)
[![python](https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg)](https://www.python.org)
[![uv](https://img.shields.io/badge/package%20manager-uv-black?style=flat-square&logo=uv)](https://github.com/astral-sh/uv)
<br/>
[![ruff](https://img.shields.io/badge/code%20style-ruff-black?style=flat-square&logo=ruff)](https://github.com/astral-sh/ruff)
[![pre-commit](https://results.pre-commit.ci/badge/github/Christoph-UGameGerm/nonebot-plugin-fiqo/master.svg)](https://results.pre-commit.ci/latest/github/Christoph-UGameGerm/nonebot-plugin-fiqo/master)

</div>

## 📖 介绍

本插件为针对游戏Prosperous Universe，基于其社区数据查询项目FIO与翻译平台Weblate开发的适用于QQ的游戏内数据查询插件

开发与测试基于OneBot v11 + NapCatQQ与Console适配器，其余适配器暂不保证可用性。

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-fiqo --upgrade
使用 **pypi** 源安装

    nb plugin install nonebot-plugin-fiqo --upgrade -i "https://pypi.org/simple"
使用**清华源**安装

    nb plugin install nonebot-plugin-fiqo --upgrade -i "https://pypi.tuna.tsinghua.edu.cn/simple"


</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details open>
<summary>uv</summary>

    uv add nonebot-plugin-fiqo
安装仓库 master 分支

    uv add git+https://github.com/Christoph-UGameGerm/nonebot-plugin-fiqo@master
</details>

<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-fiqo
安装仓库 master 分支

    pdm add git+https://github.com/Christoph-UGameGerm/nonebot-plugin-fiqo@master
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-fiqo
安装仓库 master 分支

    poetry add git+https://github.com/Christoph-UGameGerm/nonebot-plugin-fiqo@master
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_fiqo"]

</details>

<details>
<summary>使用 nbr 安装(使用 uv 管理依赖可用)</summary>

[nbr](https://github.com/fllesser/nbr) 是一个基于 uv 的 nb-cli，可以方便地管理 nonebot2

    nbr plugin install nonebot-plugin-fiqo
使用 **pypi** 源安装

    nbr plugin install nonebot-plugin-fiqo -i "https://pypi.org/simple"
使用**清华源**安装

    nbr plugin install nonebot-plugin-fiqo -i "https://pypi.tuna.tsinghua.edu.cn/simple"

</details>


## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

| 配置项  | 必填  | 默认值 |   说明   |
| :-----: | :---: | :----: | :------: |
| FIQO__weblate__api_token | 否 | 无 | 查询物品或建筑的本地化字段时使用的官方Weblate平台API Token。未配置会导致部分查询字段无法获取 |
| FIQO__game__all_ingame_cxs | 否 | ["AI1", "CI2", "CI1", "IC1", "NC2", "NC1"] | 允许查询的游戏内商品市场代码列表 |
| FIQO__game__all_ingame_fas | 否 | {"AI": "AI", "CI": "CI", "IC": "IC", "NC": "NC", "INS": "IC", "NEO": "NC"} | 允许使用的派系自定义称呼，及其与游戏内派系代码的映射关系。用于群昵称格式验证 |

以下配置管理该插件命令的权限组，可用于控制群内命令滥用导致的刷屏。下表按照权限由高到低排序，高权限组用户自动拥有低权限组权限。使用OneBot V11时每个id的格式为`"onebot:{user_id}"`

| 配置项  | 必填  | 默认值 |   说明   |
| :-----: | :---: | :----: | :------: |
| FIQO__users__admin | 否 | 无 | 开发组权限白名单 |
| FIQO__users__superusers | 否 | 无 | 超级用户权限白名单。群主/群管理员自动归入该权限组
| FIQO__users__testusers | 否 | 无 | 测试用户权限白名单
| FIQO__users__group_level_threshold | 否 | 5 | 普通用户权限的群内等级最低限制。普通用户的准入条件为群等级高于该限制 **或** 拥有群头衔 |

以下配置管理该插件返回消息的格式。控制插件的合并转发行为等。

| 配置项  | 必填  | 默认值 |   说明   |
| :-----: | :---: | :----: | :------: |
| FIQO__format__single_response_line_limit | 否 | 10 | 大于该行数的消息会被转为合并转发形式发送 |
| FIQO__format__single_response_char_limit | 否 | 400 | 大于该字数的消息会被转为合并转发形式发送 |
| FIQO__format__list_item_lead | 否 | " - " | 消息中格式化查询所返回的列表数据时使用的表头 |

## 🎉 使用
### 指令表
持续更新中，可使用nonebot-plugin-alconna内置的help插件提供的help命令查询命令列表
