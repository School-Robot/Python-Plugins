import os
import configparser
import json
import threading
import requests
import schedule
import time

"""
百度贴吧信阳师范学院吧监听
"""

plugin_name = "tieba"
plugin_id = "xynu.xiaofei.tieba"
plugin_version = "1.0.0"
plugin_author = "xia0fe1"
plugin_desc = "贴吧监听插件"

group = 838365570  # 需要发送消息的QQ群


class Plugin(object):
    plugin_methods = {
        'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
        'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
        'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
        'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
        'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'},
        'private_message': {'priority': 30000, 'func': 'private_message', 'desc': '私聊消息处理'},
        'job': {'priority': 30000, 'func': 'job', 'desc': '贴吧监听'},
        'timeevent': {'priority': 30000, 'func': 'schedule', 'desc': '创建定时任务'}
        }
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
        try:
            with open(os.path.join(self.dir, 'time.json'),'r') as f:
                self.time = json.loads(f.read())
        except:
            self.time = {'last_time': 0 }
            with open(os.path.join(self.dir, 'time.json'),'w') as f:
                f.write(json.dumps(self.time))

        thread = threading.Thread(target=self.timeevent)
        thread.start()
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.log.info("Plugin unregister")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, msg, font,
                      sender):

        return False

    def job(self):
        url = "https://tieba.baidu.com:443/mg/f/getFrsData?kw=%E4%BF%A1%E9%98%B3%E5%B8%88%E8%8C%83%E5%AD%A6%E9%99%A2&rn=10&pn=1&is_good=0&cid=0&sort_type=1&fr=sharewise&default_pro=0&only_thread_list=0&qq-pf-to=pcqq.c2c"
        # try:
        response = requests.get(url).json()

        new_post = response['data']['thread_list'][1]
        title = new_post['title']  # 帖子标题
        text = new_post['abstract'][0]['text']  # 内容预览
        link = "https://tieba.baidu.com/p/" + str(new_post['id'])  # 链接
        create_time = new_post['create_time']  # 创建时间

        if create_time > self.time['last_time']:
            self.time['last_time'] = create_time
            with open(os.path.join(self.dir, 'time.json'),'w') as f:
                f.write(json.dumps(self.time))
                
            need_send_message = f'有新帖子\n标题：{title}\n内容：{text}\n链接：{link}'
            self.util.send_group_msg(self.auth, group, need_send_message)
            return True


    def timeevent(self):
        schedule.every(10).minutes.do(self.job)

        while True:
            schedule.run_pending()
            time.sleep(1)
