"""
入群欢迎设置
"""

plugin_name = "enhanced_auto_reply"
plugin_id = "sdust.emojiZ.group_join_welcome"
plugin_version = "1.0.1"
plugin_author = "Z"
plugin_desc = "入群欢迎设置"


class Plugin(object):
    plugin_methods = {'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
                      'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
                      'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
                      'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
                      'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'},
                      'group_increase': {'priority': 30000, 'func': 'group_increase', 'desc': '入群事件处理'}
                      }
    plugin_commands = {'group_join_welcome': 'group_join_welcome_command'}
    plugin_auths = {'send_group_msg', 'get_msg', 'get_image'}
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
        self.admin = ""
        self.dir = dir
        if self.admin == "":
            self.log.warning("未设置管理员,请在控制台使用 group_join_welcome set <QQ>设置管理员")
        self.log.info("Plugin register")

    def enable(self, auth):
        self.auth = auth
        self.welcome_word = {}
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.welcome_word = {}
        self.log.info("Plugin unregister")

    def group_join_welcome_command(self, cmd):
        if len(cmd) == 2:
            if cmd[0] == 'set':
                try:
                    self.admin = str(cmd[-1])
                    self.log.info("设置成功")
                except ValueError:
                    self.log.warning('参数错误')
            else:
                self.log.warning('参数错误')
        else:
            self.log.warning('参数错误')

    def group_increase(self, time, self_id, sub_type, group_id, operator_id, user_id):
        if str(group_id) in self.welcome_word.keys():
            need_send = self.util.cq_at(qq=user_id) + "\n" + self.welcome_word.get(str(group_id))
            self.util.send_group_msg(self.auth, group_id, need_send)
            return True
        return False

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message,
                      font, sender):
        if str(raw_message).startswith("#设置欢迎词 "):
            if str(user_id) == self.admin:
                word = str(raw_message).replace("#设置欢迎词 ", "")
                self.welcome_word[str(group_id)] = word
                self.util.send_group_msg(self.auth, group_id, "入群欢迎词设置成功")
                return True
            else:
                self.util.send_group_msg(self.auth, group_id, "无权限设置")
                return True
        if str(raw_message).startswith("#删除欢迎词"):
            if str(user_id) == self.admin:
                if str(group_id) in self.welcome_word.keys():
                    del self.welcome_word[str(group_id)]
                    self.util.send_group_msg(self.auth, group_id, "删除成功")
                    return True
                else:
                    self.util.send_group_msg(self.auth, group_id, "本群暂无换欢迎词")
                    return False
            else:
                self.util.send_group_msg(self.auth, group_id, "无权限设置")
                return True
        if str(raw_message).startswith("#修改欢迎词 "):
            if str(user_id) == self.admin:
                word = str(raw_message).replace("#修改欢迎词 ", "")
                self.welcome_word[str(group_id)] = word
                self.util.send_group_msg(self.auth, group_id, "入群欢迎词修改成功")
                return True
            else:
                self.util.send_group_msg(self.auth, group_id, "无权限设置")
                return True
        return False
