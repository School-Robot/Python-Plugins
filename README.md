# Python-Plugins
用于 https://github.com/School-Robot/Plugin-Loader 的插件

## 插件列表

- 测试插件
- 单文件样例插件
- 天气查询
- 简单的自动回复
- 舔狗插件
- 千问插件

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

### 千问插件
群内发送`/gpt [你的问题]`即可与千问大模型对话

首次使用需要安装OpenAI SDK 与DashScope SDK 并在阿里通义千问官网申请SK

### 音乐搜索插件

用于搜索国内音乐平台的音乐

首次使用需要使用控制台命令设置管理员，也可以在`config.json`中设置

控制台命令：`music_search set <管理员QQ号>`

管理员在群内可以使用命令`/音乐搜索`切换在本群插件的启用情况

- `/网易云音乐 搜索关键词` 搜索网易云音乐，也可以不设置搜索关键词，会有交互提示
- `/QQ音乐 搜索关键词` 搜索QQ音乐，也可以不设置搜索关键词，会有交互提示

其中，命令触发语可以在`config.json`中修改

在获取到搜索结果后，可发送：`歌曲序号 类别选择`获取相应结果
类别选择：

- `封面`  获取歌曲封面图片URL
- `歌词`  获取歌曲歌词URL
- `链接`  获取歌曲播放链接
- `语音`  在群内发送歌曲的语音
- `歌词图片`  歌曲歌词图片生成
