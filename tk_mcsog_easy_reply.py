import json
import threading

class Plugin(object):
    plugin_methods={'register':{'priority':30000,'func':'register','desc':'注册插件'},'enable':{'priority':30000,'func':'enable','desc':'启用插件'},'disable':{'priority':30000,'func':'disable','desc':'禁用插件'},'unregister':{'priority':30000,'func':'unregister','desc':'卸载插件'},'group_message':{'priority':30000,'func':'group_message','desc':'群消息处理'}}
    plugin_commands={}
    plugin_auths={'send_group_msg'}
    auth=''
    log=None
    status=None
    bot=None
    util=None
    dir=None
    stop=False
    config=None
    engine=None
    session=None
    dict_list={}

    def register(self,logger,util,bot,dir):
        self.log=logger
        self.bot=bot
        self.util=util
        self.dir=dir
        self.log.info("Plugin register")

    def enable(self,auth):
        self.auth=auth
        try:
            with open(self.dir+'/dicts.json','r') as f:
                self.dict_list=json.loads(f.read())
        except:
            with open(self.dir+'/dicts.json','w') as f:
                f.write(json.dumps({'test':'test'}))
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        try:
            with open(self.dir+'/dicts.json','w') as f:
                f.write(json.dumps(self.dict_list))
        except:
            pass
        self.log.info("Plugin unregister")

    def group_message(self,time,self_id,sub_type,message_id,group_id,user_id,anonymous,message,raw_message,font,sender):
        if raw_message.startswith('+xx'):
            if user_id == 1822245039:
                msgs=raw_message.split(' ')
                if len(msgs) == 3:
                    self.dict_list[msgs[1]]=msgs[2]
                    self.util.send_group_msg(self.auth,group_id,'已添加')
                    return True
                else:
                    self.util.send_group_msg(self.auth,group_id,'参数错误')
                    return True
            else:
                self.util.send_group_msg(self.auth,group_id,'无权限')
                return True
        if raw_message.startswith('-xx'):
            if user_id == 1822245039:
                msgs=raw_message.split(' ')
                if len(msgs) == 2:
                    try:
                        del self.dict_list[msgs[1]]
                        self.util.send_group_msg(self.auth,group_id,'已删除')
                    except:
                        self.util.send_group_msg(self.auth,group_id,'未找到')
                    return True
                else:
                    self.util.send_group_msg(self.auth,group_id,'参数错误')
                    return True
            else:
                self.util.send_group_msg(self.auth,group_id,'无权限')
                return True
        if raw_message in self.dict_list:
            self.util.send_group_msg(self.auth,group_id,self.dict_list[raw_message])
            return False
        return False


plugin_name="简单的自动回复"
plugin_id="tk.mcsog.easy_reply"
plugin_version="1.0.0"
plugin_author="f00001111"
plugin_desc="简单的自动回复插件"