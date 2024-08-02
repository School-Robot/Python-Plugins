import json
import os
import configparser

""""
本插件需要openAI sdk 与DashScope SDK
以及阿里云通译千问模型sk
使用前请确保以具备此三者
并将讲sk写入配置文件
"""

plugin_name = "qwen_talk"
plugin_id = "sdust.emojiZ.qwen_talk"
plugin_version = "1.0.1"
plugin_author = "Z"
plugin_desc = "一款基于通译千问大模型的AI对话插件"

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
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        self.log.info("Plugin register")

    def enable(self, auth):
        self.auth = auth
        config_file_name = 'sk_config.ini'
        config_path = os.path.join(self.dir, config_file_name)
        config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            my_sk = ""
            config['QwenSK'] = {
                "qwen_sk": my_sk
            }
            # 写入文件
            with open(config_path, 'w') as configfile:
                config.write(configfile)
            self.api_key = my_sk
        else:
            config.read(config_path)
            self.api_key = config.get("QwenSK", "qwen_sk", fallback="")
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.log.info("Plugin unregister")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message,
                      font, sender):
        if self.api_key == "":
            return False
        if raw_message.startswith("/gpt "):
            reply_info = self.util.cq_reply(message_id)
            try:
                request_message = raw_message[5:]
                client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 填写DashScope服务的base_url
                )

                completion = client.chat.completions.create(
                    model="qwen-turbo",
                    messages=[
                        {'role': 'user', 'content': request_message}],
                    temperature=0.8,
                    top_p=0.8,
                    extra_body={"enable_search": True}
                )
                json_data = json.loads(completion.model_dump_json())
                reply_info += json_data['choices'][0]['message']['content']
            except Exception:
                reply_info += "接口错误 请重试"
                self.util.send_group_msg(self.auth, group_id, reply_info)
                return False
            self.util.send_group_msg(self.auth, group_id, reply_info)
            return True
        return False
