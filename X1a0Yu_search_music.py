"""
查询音乐
"""

import requests
import re
from urllib.parse import quote

plugin_name = "search_music"
plugin_id = "X1a0Yu.search.music"
plugin_version = "1.0.0"
plugin_author = "X1a0Yu"
plugin_desc = "点歌"

API_PRE_FIX = "http://api.caonmtx.cn/api/wangyi.php?msg="
API_PRE_FIX1 = "&n=1"
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

        API_PRE_FIX = "http://api.caonmtx.cn/api/wangyi.php?msg="
        API_PRE_FIX1 = "&n=1"

        if raw_message.startswith('音乐'):
            res = raw_message.replace('音乐-', '', 1)
            full_url = API_PRE_FIX + res + API_PRE_FIX1

            try:
                response = requests.get(full_url).json()
                if response['code'] == 500:
                    self.util.send_group_msg(self.auth, group_id, "接口1错误，请重试")
                else:
                    data = response.get('data', {})
                    if not isinstance(data, dict):
                        self.util.send_group_msg(self.auth, group_id, "数据格式错误，请重试")
                    else:
                        src = data.get('src')
                        if src is None:
                            self.util.send_group_msg(self.auth, group_id, "数据中未找到音乐链接，请重试")
                        else:
                            need_send_message = ""
                            need_send_message += self.util.cq_reply(message_id)
                            # need_send_message += src
                            need_send_message = "[CQ:record,file={}]".format(src)
                            self.util.send_group_msg(self.auth, group_id, need_send_message)
                return True
            except requests.RequestException as e:
                self.util.send_group_msg(self.auth, group_id, "请求失败，请重试")
                print(f"Request failed: {e}")
                return True
            except ValueError as e:
                self.util.send_group_msg(self.auth, group_id, "无法解析服务器响应，请重试")
                print(f"Failed to parse JSON: {e}")
                return True
            except KeyError as e:
                self.util.send_group_msg(self.auth, group_id, "服务器响应缺少必要字段，请重试")
                print(f"Missing key in response: {e}")
                return True
        else:
            return False

