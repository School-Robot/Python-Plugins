import json
import os
import random
import time as te
from apscheduler.schedulers.background import BackgroundScheduler

class Plugin(object):
    plugin_methods={
        "register":{'priority':30000,'func':'register','desc':'注册插件'},
        'enable':{'priority':30000,'func':'enable','desc':'启用插件'},
        'disable':{'priority':30000,'func':'disable','desc':'禁用插件'},
        'unregister':{'priority':30000,'func':'unregister','desc':'卸载插件'},
        'group_message':{'priority':20000,'func':'group_message','desc':'群消息处理'},
        'private_message':{'priority':20000,'func':'private_message','desc':'私聊消息处理'},
        'group_request':{'priority':20000,'func':'group_request','desc':'加群请求'}
        }
    plugin_commands={'bot_check':'bot_check_command','help':'bot_check set <管理员QQ号> - 设置管理员'}
    plugin_auths={'send_group_msg','get_msg','set_group_kick','set_group_ban','set_group_add_request','get_group_info','get_group_member_list','get_group_member_info','mark_private_msg_as_read'}
    auth=''
    log = None
    status = None
    bot = None
    util = None
    dir = None
    config={'manager':0,'group':[]}
    dict_list={}
    check_list={}

    def register(self, logger, util, bot, dir):
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        self.log.info("Plugin register")
    
    def enable(self,auth):
        self.auth = auth
        try:
            with open(os.path.join(self.dir, 'all_ban_id.json'),'r') as f:
                self.dict_list=json.loads(f.read())
        except:
            with open(os.path.join(self.dir, 'all_ban_id.json'),'w') as f:
                f.write(json.dumps({}))
        try:
            with open(os.path.join(self.dir,'config.json'),'r') as f:
                self.config=json.loads(f.read())
        except:
            with open(os.path.join(self.dir,'config.json'),'w') as f:
                f.write(json.dumps(self.config))
        self.timeoutcheck()
        if self.config['manager']==0:
            self.log.warning("未设置管理员,在控制台使用bot_check set <管理员QQ号> 命令设置管理员")
        self.log.info("Plugin enable")
    def disable(self):
        self.log.info("Plugin disable")
    def unregister(self):
        try:
            with open(self.dir+'/all_ban_id.json','w') as f:
                f.write(json.dumps(self.dict_list))
        except:
            pass
        try:
            with open(self.dir+'/config.json','w') as f:
                f.write(json.dumps(self.config))
        except:
            pass
        self.log.info("Plugin unregister")

    def group_request(self,time,self_id,sub_type,group_id,user_id,comment,flag):
        if group_id not in self.config['group']:
            return False
        if str(user_id) in self.dict_list:
            self.util.set_group_add_request(self.auth,flag,sub_type,False,f"你在黑名单中,误ban联系{self.config['manager']}处理")
            return False
        random.seed(te.time())
        num1 = random.randint(0,100)
        num2 = random.randint(0,100)
        self.util.set_group_add_request(self.auth,flag,sub_type,True)
        self.util.set_group_ban(self.auth,group_id,user_id)
        self.util.send_group_msg(self.auth,group_id,f"[CQ:at,qq={user_id}]请在240秒内向我私聊回答 {num1}+{num2}=? ,如有任何疑问请联系({self.config['manager']})")
        finall = num1 + num2
        self.check_list[(user_id,str(finall))]={"group_id":group_id,"timestamp":te.time()}
        return False
    def private_message(self,time,self_id,sub_type,message_id,user_id,message,raw_message,font,sender):
        if (user_id,raw_message) in self.check_list:
            self.util.set_group_ban(self.auth,self.check_list[(user_id,raw_message)]['group_id'],user_id,0)
            self.util.send_group_msg(self.auth,self.check_list[(user_id,raw_message)]['group_id'],f"[CQ:at,qq={user_id}]认证成功,欢迎!")
            del self.check_list[(user_id,raw_message)]
            self.util.mark_private_msg_as_read(self.auth,user_id)
    def group_message(self,time,self_id,sub_type,message_id,group_id,user_id,anonymous,message,raw_message,font,sender):
        role =sender['role']
        if user_id == self.config['manager'] or role=='owner' or role == 'admin':
            if raw_message == '开启加群验证':
                if user_id == self.config['manager']:
                    if self.config['group'].count(group_id) != 0:
                        self.util.send_group_msg(self.auth,group_id,"该群组已开启不需要开启")
                    else:
                        self.config['group'].append(group_id)
                        self.util.send_group_msg(self.auth,group_id,"已开启")
                else:
                    self.util.send_group_msg(self.auth,group_id,f"请联系{self.config['manager']}开启")
            elif raw_message == '关闭加群验证':
                if self.config['group'].count(group_id) == 0:
                    self.util.send_group_msg(self.auth,group_id,"该群组未开启加群验证功能")
                else:
                    self.config['group'].remove(group_id)
                    self.util.send_group_msg(self.auth,group_id,"已关闭")
        if group_id not in self.config['group']:
            return False
        if user_id == self.config['manager'] or role=='owner' or role == 'admin':
            msg1 = raw_message.strip(' ')
            msg=msg1.split(' ')
            if msg[0] == "拉黑":
                
                if len(msg) == 3:
                    if msg[1].startswith('[CQ:at,qq='):
                        index = msg[1].index(']')
                        msg[1]= msg[1][10:index]
                        msg[1]= self.is_number(msg[1])
                    if msg[1]:
                        if msg[1] == self_id:
                            self.util.send_group_msg(self.auth,group_id,"?不是哥们")
                        if str(msg[1]) in self.dict_list:
                            self.util.send_group_msg(self.auth,group_id,f"{str(msg[1])}已经被拉黑,不需要再拉黑")
                        else:
                            self.dict_list[str(msg[1])] = {"who_ban":user_id,'reason':msg[2]}
                            self.util.send_group_msg(self.auth,group_id,f"{str(msg[1])}已拉黑")
                        
                        for i in self.config['group'].copy():#拉黑后踢人或者检查黑名单
                            ban_check="以下qq已被拉黑,请管理尽快清理\n"
                            group_list = self.util.get_group_member_list(self.auth,i)[1]
                            bot_is_in,bot_info = self.util.get_group_member_info(self.auth,i,self_id)
                            if bot_is_in==False:
                                self.config['group'].remove(i)
                                continue
                            bot_info = bot_info['role']
                            admin_at = {"admin_qq":None,"time":00000}
                            for j in group_list:
                                if j['role']=='admin' or j['role'] == 'owner':
                                    # print(j['nickname']+str(j['last_sent_time'])+"\n")
                                    if j['last_sent_time'] > admin_at['time']:
                                        admin_at['admin_qq']=j['user_id']
                                        admin_at['time']= j['last_sent_time']
                                if str(j['user_id']) in self.dict_list:
                                    if bot_info == 'owner' or bot_info == 'admin':
                                        self.util.set_group_kick(self.auth,i,j['user_id'])
                                    else:
                                        ban_check+=f"{j['user_id']} 原因:{self.dict_list[str(j['user_id'])]['reason']}\n"
                            if ban_check=="以下qq已被拉黑,请管理尽快清理\n":
                                continue
                            ban_check=f"[CQ:at,qq={admin_at['admin_qq']}]\n"+ban_check
                            if bot_info != 'owner' and bot_info != 'admin':
                                self.util.send_group_msg(self.auth,i,ban_check)
                            
                    else:
                        self.util.send_group_msg(self.auth,group_id,"qq号错误: \n格式:拉黑 <qq号或at> <原因>\n 仅支持管理员操作")

                else:
                    self.util.send_group_msg(self.auth,group_id,"参数错误: \n 拉黑 <qq号或at> <原因>\n仅支持管理员操作")           
            elif msg[0] == '拉白':
                if len(msg)==2:
                    msg[1] = self.is_number(msg[1])
                    if msg[1]:
                        if str(msg[1]) in self.dict_list:
                            del self.dict_list[str(msg[1])]
                            self.util.send_group_msg(self.auth,group_id,f"{msg[1]}已从黑名单中移除")
                        else:
                            self.util.send_group_msg(self.auth,group_id,f"{msg[1]}未在黑名单中")
                    else:
                        self.util.send_group_msg(self.auth,group_id,"qq号错误: \n格式:拉白 <qq号>\n仅支持管理员操作")
                else:
                    self.util.send_group_msg(self.auth,group_id,"参数错误: \n格式:拉白 <qq号>\n仅支持管理员操作")
            elif raw_message == '拉黑名单':
                ban_list = f"[CQ:at,qq={user_id}]"
                for i in self.dict_list:
                    ban_list+=f"\n\n{i}原因:{self.dict_list[i]['reason']}\n处理人:{self.dict_list[i]['who_ban']}"
                self.util.send_group_msg(self.auth,group_id,ban_list)
                return False

        return False
    def timeoutcheck(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.timeout_group_kick,'interval',minutes=1)
        scheduler.start()
    def timeout_group_kick(self):
        for i in self.check_list.copy():
            if te.time() - self.check_list[i]['timestamp']>240:
                self.util.set_group_kick(self.auth,self.check_list[i]['group_id'],i[0])
                del self.check_list[i]
                self.util.mark_private_msg_as_read(self.auth,i[0])

    def bot_check_command(self,cmd):
        if len(cmd)==2:
                if cmd[0]=='set':
                    try:
                        self.config['manager']=int(cmd[1])
                        with open(os.path.join(self.dir,'config.json'),'w') as f:
                            f.write(json.dumps(self.config))
                        self.log.info('设置成功')
                    except:
                        self.log.warning('参数错误')
                else:
                    self.log.warning('参数错误')
        else:
            self.log.warning('参数错误')
    def is_number(self,num):
        try:
            num1 = int(num)
            return num1
        except ValueError:
            return False


plugin_name="加群机器人验证+多群黑名单"
plugin_id="jxufe.qiuyuyang.botCheck"
plugin_version="1.1.0"
plugin_author="qiuyuyang"
plugin_desc="通过简单算术运算判断是否为真人"
