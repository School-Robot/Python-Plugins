# Python-Plugins
用于 https://github.com/School-Robot/Plugin-Loader 的插件

## 插件列表

- 测试插件
- 单文件样例插件
- 天气查询
- 简单的自动回复
- 舔狗插件
- AI对话插件
- 音乐搜索插件
- 图片修改插件
- Stable Diffusion生成插件
- 入群验证+多群黑名单
- 今天吃什么分校区版

## 插件说明

### 测试插件

用于测试以插件包形式编写的插件

### 单文件样例插件

用于测试单文件形式编写的插件

### 天气查询

用于群内查询天气信息，使用方式：`查询天气 地名`

### 简单的自动回复

用于添加和删除群内自动回复

首次使用时需要使用控制台命令设置管理员，也可在`config.json`中设置

控制台命令：`easy_reply set <管理员QQ号>`

群内使用命令添加或删除词条

- `+xx 触发语 回复语` 添加词条
- `-xx 触发语` 删除词条

群内命令可在`config.json`中修改

群内发送内容匹配到词条会向群内发送回复语

### 舔狗插件

群内发送`舔狗日记`可触发

### AI对话插件
群内艾特机器人账号加上`[你的问题]`即可与AI大模型对话

首次使用需要安装OpenAI SDK 与DashScope SDK 并在deep bricks官网申请SK，并在代码中填写sk和管理员QQ号

发送`模型列表`查看当前可用模型

发送`#gptc [模型名]`切换使用的模型

### 音乐搜索插件

用于搜索国内音乐平台的音乐

首次使用需要使用控制台命令设置管理员，也可以在`config.json`中设置

控制台命令：`music_search set <管理员QQ号>`

管理员在群内可以使用命令`/音乐搜索`查看帮助
```
/音乐搜索 帮助 - 显示此帮助信息
/音乐搜索 自动撤回 - 切换自动撤回功能的开启或关闭
/音乐搜索 功能 <触发器> - 切换指定功能的启用或禁用
/音乐搜索 切换 - 切换本群的插件启用状态
/音乐搜索 查看配置 - 发送当前配置的 JSON

触发器包括: 封面、链接、歌词、歌词图片、语音
```

- `/网易云音乐 搜索关键词` 搜索网易云音乐，也可以不设置搜索关键词，会有交互提示
- `/QQ音乐 搜索关键词` 搜索QQ音乐，也可以不设置搜索关键词，会有交互提示
- `/酷狗音乐 搜索关键词` 搜索酷狗音乐，也可以不设置搜索关键词，会有交互提示

其中，命令触发语可以在`config.json`中修改

在获取到搜索结果后，可发送：`歌曲序号 类别选择`获取相应结果
类别选择：

- `封面`  获取歌曲封面图片URL
- `歌词`  获取歌曲歌词URL
- `链接`  获取歌曲播放链接
- `语音`  在群内发送歌曲的语音
- `歌词图片`  歌曲歌词图片生成

API接口源码(修改后的meting-api)：[![GitHub](https://img.shields.io/badge/GitHub-cnrenil/meting--api-blue)](https://github.com/cnrenil/meting-api)

### 图片修改插件

用于修改图片，给图片增加效果等

用法：在群内回复图片，图片可为gif或者表情。

可用操作可以在群内发送`#可用操作`查看

可用操作包括：
| 操作         | 操作         | 操作         | 操作         |
|--------------|--------------|--------------|--------------|
| 旋转90度     | 旋转180度    | 旋转270度    | 锐化         |
| 黑白         | 增加亮度     | 减少亮度     | 增加对比度   |
| 减少对比度   | 边缘检测     | 浮雕效果     | 反色         |
| 降噪         | 添加噪点     | 老照片       | 马赛克       |
| 增加饱和度   | 减少饱和度   | 水平翻转     | 垂直翻转     |
| 素描效果     | 水彩效果     | 油画效果     | 添加边框     |
| 高斯模糊     | 波浪效果     | 漩涡效果     | 增加色温     |
| 减少色温     | 镜像         |              |              |


### Stable Diffusion生成插件

接入SD API，生成图片

配置文件：首次运行之后，请在`data/sdust.dayi.stable_diffusion/sd_config.ini`配置API

用法：在`/sd 提示词`
### 入群验证+多群黑名单

入群验证:自动同意入群请求,并禁言新入群成员要求私聊机器人回答简单的加法运算,为确保不会被风控,私聊消息**不会**做回复，只有在规定时间内没有正确回答问题才会踢人,答案错误**不做处理**，验证消息:

```txt
@<新入群的人>请在240秒内向我私聊回答 <100以内数字>+<100以内数字>=? ,如有任何疑问请联系(<插件管理员>)
```

多群黑名单:多群公用黑名单,只有各群管理员和插件管理员可以拉黑/拉白,在`bot`有管理员的群里将**直接踢出**黑名单内的人，没有管理员的群会发送以下消息,踢人和以下消息只会在拉黑后触发一次

拉黑名单:可用于查看拉黑名单，和对应的操作人qq号

```txt
以下qq已被拉黑,请管理尽快清理
<qq号> 原因:<原因>
@<随机管理员>
```

初次使用需要在终端设置插件管理员

`bot_check set <管理员QQ号>`

开启插件指令(仅限插件管理员)

`开启加群验证`

关闭插件指令(插件管理员和各群管理员)

`关闭加群验证`

拉黑/拉白指令(插件管理员和各群管理员)

`拉黑 <qq号或at> <原因>`
`拉白 <qq号>`

拉黑名单指令(插件管理员和各群管理员)

`拉黑名单指令`

### 今天吃什么分校区版

发送`吃什么帮助`获取帮助

在首次运行后
- 数据需自行填入`[加载器根目录]/data/jxufe.qiuyuyang.eatWhat/eatWhat.json`
- 配置文件需自行填入`[加载器根目录]/data/jxufe.qiuyuyang.eatWhat/settings.json`

`eatWhat.json`

```
{"msg":[{"foodName":string,"storeName":string,"location":string,"campus":麦庐/枫林/蛟桥,"takeout":bool},],"total":int}
```
举个栗子
```json
{
    "msg": [
        {
            "foodName": "烧鹅饭",
            "storeName": "深井烧鹅",
            "location": "麦庐二食堂一楼",
            "campus": "麦庐",
            "takeout": false
        },
        {
            "foodName": "腊肉拌面",
            "storeName": "朱家小馆",
            "location": "新商业街二楼",
            "campus": "麦庐",
            "takeout": false
        }],
        "total": 2
}
```

配置文件`settings.json`

```json
{
    "url":""
,"campus":["麦庐","枫林"]
}
```
- `url`:可配置数据收集的提示,在每一条消息后面都会显示，未配置则不会显示，可填入共享文档的url
- `campus`:填入校区即可