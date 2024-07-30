"""
查询指定城市未来7天的天气
"""

import requests

plugin_name = "query_weather"
plugin_id = "com.example.query_weather"
plugin_version = "1.0.0"
plugin_author = "Z"
plugin_desc = "查询天气"

API_PRE_FIX = "https://api.oioweb.cn/api/weather/weather?city_name="


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
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.log.info("Plugin unregister")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message,
                      font, sender):
        if raw_message.startswith('查询天气'):
            msg = raw_message.split(' ')
            if msg[0] == '查询天气':
                if len(msg) == 2:
                    full_url = API_PRE_FIX + str(msg[1])
                    try:
                        response = requests.get(full_url).json()
                        if response['code'] == 500:
                            self.util.send_group_msg(self.auth, group_id, "接口错误，请重试")
                        else:
                            res = response['result']['forecast_list'][1:5]
                            need_send_message = ""
                            need_send_message += self.util.cq_reply(message_id)
                            for i in res:
                                need_send_message += f"日期：{i['date']}  天气：{i['condition']} 温度：{i['low_temperature']}~{i['high_temperature']}"
                                need_send_message += "\n"
                            self.util.send_group_msg(self.auth, group_id, need_send_message)
                        return True
                    except:
                        self.util.send_group_msg(self.auth, group_id, "接口错误，请重试")
                        return True
                else:
                    self.util.send_group_msg(self.auth, group_id, "请按照格式输入，如：查询天气 北京")
                    return True
            else:
                return False
        else:
            return False
