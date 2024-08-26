import json
import os
import configparser
from .sd import group_message_func
from .config import config_init


class Plugin(object):
    plugin_methods = {'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
                      'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
                      'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
                      'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
                      'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'}}
    plugin_commands = {}
    plugin_auths = {'send_group_msg', 'upload_group_file'}
    auth = ''
    log = None
    status = None
    bot = None
    util = None
    dir = None
   
    def __init__(self):
      pass
    
    def register(self, logger, util, bot, dir):
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        self.log.info("Stable Diffusion Plugin registered")
   
    def enable(self, auth):
        self.auth = auth
        self.log.info("加载配置文件中..")
        try:
           self.configer = config_init(self.dir)
           api_key = self.configer.get("StableDiffusion", "api_key", fallback="")
           self.log.info(f"API_KEY:{api_key}")
           api_url = self.configer.get("StableDiffusion", "api_url", fallback="")
           self.log.info(f"API_URL:{api_url}")
           default_neg_prompt = self.configer.get("StableDiffusion", "DEFAULT_NEG_PROMPT", fallback="")
           self.log.info(f"NEG_PROMPT:{default_neg_prompt}")
           self.log.info("加载配置成功")
        except Exception as e:
           self.log.error("配置文件出错")

        self.log.info("Stable Diffusion Plugin enabled")
   
    def disable(self):
        self.log.info("Stable Diffusion Plugin disabled")
       
    def unregister(self):
        self.log.info("Stable Diffusion Plugin unregistered")
       
    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender):
        if raw_message.startswith("/sd "):
          code,ret = group_message_func(time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender,self.util,self.dir,configer=self.configer,logger=self.log)
          if code:  
            self.util.send_group_msg(self.auth,group_id,ret)
          return