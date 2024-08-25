import json
import os
import configparser

""""
本插件需要openAI sdk 
本插件基于deepbricks实现因此需要您的deepbriks sk

"""

plugin_name = "ai_talk"
plugin_id = "sdust.emojiZ.ai_talk"
plugin_version = "2.0.0"
plugin_author = "Z"
plugin_desc = "一款基于deepbricks的大模型AI对话插件"

from openai import OpenAI

from openai import OpenAI


class Plugin(object):
    plugin_methods = {'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
                      'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
                      'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
                      'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
                      'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'}}
    plugin_commands = {}
    plugin_auths = {'send_group_msg'}
    auth = ''
    log = None
    status = None
    bot = None
    util = None
    dir = None

    def register(self, logger, util, bot, dir):
        self.model_list = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o", "gpt4-turbo"]
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        self.admin = ""  # 管理qq
        self.model = "gpt-4o-mini"
        self.base_url = "https://api.deepbricks.ai/v1/"
        self.log.info("Plugin register")

    def enable(self, auth):
        self.auth = auth
        config_file_name = 'sk_config.ini'
        config_path = os.path.join(self.dir, config_file_name)
        config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            my_sk = ""  # 此处填写你的sk
            config['AI_SK'] = {
                "ai_sk": my_sk
            }
            # 写入文件
            with open(config_path, 'w') as configfile:
                config.write(configfile)
            self.api_key = my_sk
        else:
            config.read(config_path)
            self.api_key = config.get("AI_SK", "ai_sk", fallback="")
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.log.info("Plugin unregister")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message,
                      font, sender):
        if raw_message == "模型列表":
            need_send = "当前可用模型有:\n" + "\n".join(self.model_list)
            self.util.send_group_msg(self.auth, group_id, need_send)
            return True
        if raw_message.startswith("#gptc "):
            if str(user_id) != self.admin:
                self.util.send_group_msg(self.auth, group_id, "无权限")
                return True
            else:
                target_model = raw_message.split(" ", 2)[-1]
                if target_model not in self.model_list:
                    self.util.send_group_msg(self.auth, group_id, "非可用模型,请发送\'模型列表\'获取所有可用模型")
                    return True
                self.model = target_model
                self.util.send_group_msg(self.auth, group_id, f"切换成功,当前模型{self.model}")
                return True
        if self.api_key == "":
            return False
        at_bot = "[CQ:at,qq=" + str(self.bot.get_id()) + "]"
        if raw_message.startswith(at_bot):
            try:
                raw_message = raw_message.replace(at_bot, "")
                reply_info = self.util.cq_reply(message_id)
                client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                model = self.model
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "回复中不允许出现markdown语法"},
                        {"role": "system", "content": "必须简洁简短的回复用户问题"},
                        {"role": "user", "content": raw_message}
                    ]
                )
                send_info = reply_info + completion.choices[0].message.content + f"\n[+]当前使用模型:{model}"
                self.util.send_group_msg(self.auth, group_id, send_info)
                return True
            except Exception:
                self.util.send_group_msg(self.auth, group_id, "接口错误")

        return False
