#plugins_class.py
from .info import plugin_name, plugin_id, plugin_version, plugin_author, plugin_desc
from .word_management import WordManagement
from .config import config_init, get_super_admin
from .commands import *

import re
import base64
import os

class Plugin(object):
    plugin_methods = {
        'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
        'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
        'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
        'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
        'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'}
    }
    plugin_commands = {}
    plugin_auths = {'send_group_msg', 'upload_group_file'}
    auth = ''
    log = None
    status = None
    bot = None
    util = None
    dir = None
    word_manager = None
    config = None

    def __init__(self):
        pass
    
    def register(self, logger, util, bot, dir):
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        self.log.info("Word Management Plugin registered")
   
    def enable(self, auth):
        self.auth = auth
        self.config = config_init(self.dir)
        self.word_manager = WordManagement(self.dir, self.config)
        self.log.info("Word Management Plugin enabled")
   
    def disable(self):
        if self.word_manager:
            self.word_manager.close()
        self.log.info("Word Management Plugin disabled")

    def unregister(self):
        if self.word_manager:
            self.word_manager.close()
        self.log.info("Word Management Plugin unregistered")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender):
        try:
            self._group_message( time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender)
        except Exception as e:
            self.util.send_group_msg(self.auth, group_id, "命令失败："+str(e))
            
        
    def _group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender):
        alias_command = self.word_manager.get_alias(group_id, raw_message)
        if alias_command:
            raw_message = alias_command
                    
        if raw_message.startswith("#add "):
            result, response = add_word(self, message_id, group_id, user_id, message)
        elif raw_message.startswith("#addc alias add "):
            result, response = add_alias(self, message_id, group_id, user_id, raw_message)
        elif raw_message.startswith("#addc alias del "):
            result, response = delete_alias(self, message_id, group_id, user_id, raw_message)
        elif raw_message == "#listword":
            result, response = list_aliases(self, message_id, group_id)
        elif raw_message.startswith("#addc show question"):
            result, response = show_questions(self, message_id, group_id, user_id, raw_message)
            
        elif raw_message == "#listword":
            result, response = list_aliases(self, message_id, group_id)
        elif raw_message.startswith("#addc show question"):
            result, response = show_questions(self, message_id, group_id, user_id, raw_message)
        elif raw_message.startswith("#addc admin "):
            result, response = add_admin(self, message_id, group_id, user_id, raw_message)
        elif raw_message.startswith("#addc level"):
            result, response = handle_level_command(self, message_id, group_id, user_id, raw_message)
        elif raw_message.startswith("#addc del "):
            result, response = delete_word(self, message_id, group_id, user_id, raw_message)
        elif raw_message.startswith("#addc query "):
            result, response = query_word(self, message_id, group_id, user_id, raw_message)
        elif raw_message.startswith("#addc requery "):
            result, response = regex_query_word(self, message_id, group_id, user_id, raw_message)
        elif raw_message == "#show_all":
            result, response = show_all_words(self, message_id, group_id)
        elif raw_message.startswith("#addc help"):
            result, response = show_help(self, message_id, group_id, user_id, raw_message)
        else:
            response = self.word_manager.check_and_respond(group_id, raw_message)
            result = bool(response)

        if result and response:
            self.util.send_group_msg(self.auth, group_id, response)


    
    
    def show_help(self, message_id, group_id, user_id, raw_message):
        parts = raw_message.split()
        if len(parts) > 2:
            # 显示特定命令的帮助
            command = parts[2]
            help_text = get_command_help(self,command, user_id)
        else:
        # 显示所有命令的概览
            help_text = get_all_commands_help(self,user_id)
    
        return True, self.util.cq_reply(message_id) + help_text

    def process_message_with_images(self, message):
        text_parts = []
        image_urls = []

        for part in message:
            if part['type'] == 'text':
                text_parts.append(part['data']['text'])
            elif part['type'] == 'image':
                url = part['data']['url']
                image_urls.append(url)
                text_parts.append(f'[CQ:image,file={url}]')

        processed_text = ''.join(text_parts)
        return processed_text, image_urls