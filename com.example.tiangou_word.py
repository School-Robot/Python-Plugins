import json

import requests

plugin_name = "tiangou_word"
plugin_id = "com.example.tiangou_word"
plugin_version = "1.0.0"
plugin_author = "Z"
plugin_desc = "舔狗日记"


class Plugins(object):
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
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.log.info("Plugin unregister")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message,
                      font, sender):
        api_url = "https://api.dzzui.com/api/tiangou?format=json"
        response = requests.get(api_url)
        response_data = json.loads(response.text)
        if response_data['code'] == 200:
            need_send_message = ""
            need_send_message += self.util.cq_reply(message_id)
            need_send_message += f"{response_data['time']}\n{response_data['text']}"
            self.util.send_group_msg(self.auth, group_id, need_send_message)
        else:
            self.util.send_group_msg(self.auth, group_id, "接口坏了你当不了舔狗了!")
