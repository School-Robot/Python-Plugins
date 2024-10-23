import json
import os
import random
import re
"""
数据结构
{"msg":[{"foodName":string,"storeName":string,"location":string,"campus":麦庐/枫林/蛟桥,"takeout":bool},],"total":int}
"""
class Plugin(object):
    plugin_methods={
        "register":{'priority':30000,'func':'register','desc':'注册插件'},
        'enable':{'priority':30000,'func':'enable','desc':'启用插件'},
        'disable':{'priority':30000,'func':'disable','desc':'禁用插件'},
        'unregister':{'priority':30000,'func':'unregister','desc':'卸载插件'},
        'group_message':{'priority':20000,'func':'group_message','desc':'群消息处理'},
        }
    plugin_commands={}
    plugin_auths={'send_group_msg'}
    auth=''
    log = None
    status = None
    bot = None
    util = None
    dir = None
    dict_list={}
    def register(self, logger, util, bot, dir):
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        self.log.info("Plugin register")
    def enable(self,auth):
        self.auth = auth
        try:
            with open(os.path.join(self.dir,'eatWhat.json'),"r") as f:
                self.dict_list=json.loads(f.read())
        except:
            with open(os.path.join(self.dir, 'eatWhat.json'),'w') as f:
                f.write(json.dumps({}))

    def disable(self):
        self.dict_list={}
        self.log.info("Plugin disable")
    def unregister(self):
        self.dict_list={}
        self.log.info("Plugin unregister")

    def group_message(self,time,self_id,sub_type,message_id,group_id,user_id,anonymous,message,raw_message,font,sender):
        if "吃什么" in raw_message:
            if raw_message == "吃什么":
                ret = self.dict_list["msg"][random.randint(0,self.dict_list["total"]-1)]
                ret_msg=f"[at,qq=user_id]\n吃{ret["foodName"] if ret['takeout']==True else "外卖\n"+ret["foodName"]}\n在{ret['location']}\n店名:{ret['storeName']}\n校区:{ret['campus']}"
                self.auth.send_group_msg(self.auth,group_id,ret_msg)
                return True
            elif re.match(r'在..吃什么外卖',raw_message):
                new_dict = []
                num = 0
                for i in ret["msg"]:
                    if i['takeout']==True and i['campus']== raw_message[1:3]:
                        new_dict.append(i)
                        num+=1
                if new_dict==[]:
                    return False
                ret = new_dict[random.randint(0,num-1)]
                ret_msg=f"[at,qq=user_id]\n吃{ret["foodName"] if ret['takeout']==True else "外卖\n"+ret["foodName"]}\n在{ret['location']}\n店名:{ret['storeName']}\n校区:{ret['campus']}"
                self.auth.send_group_msg(self.auth,group_id,ret_msg)
                return True
            elif re.match(r'在..吃什么',raw_message):
                
                new_dict = []
                num = 0
                for i in ret["msg"]:
                    if i['takeout']==False and i['campus']== raw_message[1:3]:
                        new_dict.append(i)
                        num+=1
                if new_dict==[]:
                    return False
                ret = new_dict[random.randint(0,num-1)]
                ret_msg=f"[at,qq=user_id]\n吃{ret["foodName"] if ret['takeout']==True else "外卖\n"+ret["foodName"]}\n在{ret['location']}\n店名:{ret['storeName']}\n校区:{ret['campus']}"
                self.auth.send_group_msg(self.auth,group_id,ret_msg)
                return True
            elif raw_message=="吃什么帮助":
                ret = "秋雨样awa\n\n吃什么:三校区随机\n在麦庐/枫林/蛟桥吃什么:线下该校区随机\n在麦庐/枫林/蛟桥吃什么外卖:外卖该校区随机"
        return False
plugin_name="今天吃什么分校区版"
plugin_id="jxufe.qiuyuyang.eatWhat"
plugin_version="1.0.0"
plugin_author="qiuyuyang"
plugin_desc="发送吃什么roll道菜"