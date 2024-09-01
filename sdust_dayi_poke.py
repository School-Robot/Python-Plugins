import json
import os
import configparser
import httpx
import re, uuid

plugin_name = "poke"
plugin_id = "sdust.dayi.poke"
plugin_version = "0.0.1"
plugin_author = "dayi"
plugin_desc = "碰一碰"

AT_REPLY= "大青蛙在这里"
MOE="呱"


class Plugin(object):
    plugin_methods = {
        "register": {"priority": 30000, "func": "register", "desc": "注册插件"},
        "enable": {"priority": 30000, "func": "enable", "desc": "启用插件"},
        "disable": {"priority": 30000, "func": "disable", "desc": "禁用插件"},
        "unregister": {"priority": 30000, "func": "unregister", "desc": "卸载插件"},
        "group_message": {
            "priority": 30000,
            "func": "group_message",
            "desc": "群消息处理",
        },
        "group_poke": {"priority": 30000, "func": "group_poke", "desc": "碰一碰"},
    }
    plugin_commands = {}
    plugin_auths = {"send_group_msg", }
    auth = ""
    log = None
    status = None
    bot = None
    util = None
    dir = None

    def __init__(self):
        self.group_context = {}  # 用于存储每个群组的对话上下文
        self.group_models = {}  # 用于存储每个群组使用的模型
        self.group_context_switch = {}  # 用于存储每个群组的上下文开关状态
        

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

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender):
        # print(message)
        if message[0]['type']=='at':
          if message[0]['data']['qq']==str(self_id):
            if len(message)==1:
              self.util.send_group_msg(
                        self.auth, group_id, AT_REPLY
                    )

    def group_poke(self, time, self_id, group_id, user_id, target_id):
        self.log.info(f"接收到POKE 来自[{group_id}]的用户[{user_id}]碰了下[{target_id}]")
        if self_id == target_id:
            with httpx.Client() as client:
                try:
                    response = client.get("https://v1.hitokoto.cn/")
                    data = response.json()
                    hitokoto = data["hitokoto"]
                    source = data["from"]
                    message = (
                        f"{MOE}！{hitokoto}「{source}」"
                    )
                    self.util.send_group_msg(self.auth, group_id, message)
                except Exception as e:
                    self.util.send_group_msg(
                        self.auth, group_id, "呱！你真可爱"
                    )
