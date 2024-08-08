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
last_time = 0


class Plugin(object):
	plugin_methods = {
		'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
		'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
		'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
		'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
		'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'},
		'private_message': {'priority': 30000, 'func': 'private_message', 'desc': '私聊消息处理'},
		'job': {'priority': 30000, 'func': 'job', 'desc': '贴吧监听'},
		'timeevent': {'priority': 30000, 'func': 'schedule', 'desc': '创建任务'}
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
		global last_time
		burp0_url = "https://tieba.baidu.com:443/mg/f/getFrsData?kw=%E4%BF%A1%E9%98%B3%E5%B8%88%E8%8C%83%E5%AD%A6%E9%99%A2&rn=10&pn=1&is_good=0&cid=0&sort_type=1&fr=sharewise&default_pro=0&only_thread_list=0&qq-pf-to=pcqq.c2c"
		burp0_cookies = {
			" ab_sr": "1.0.1_NTdmOTUzMjM1ODBiZGIwYTkxZTJmM2M5NmE5NGY5MzU0OWRmZWNlNTI5NTI2NDdlNTQxMTRjOGU0OTNkZjg0YzM0ODg4YmMwY2Y1NThiZWQyOGU0NGY3ZmViMWVkOTc5OTMwNjgwOWE2MzY3Njg5YmE0NTZlZGQxNDkxMmJiZTMzYWM3NDg0ODA5OGQ5YzRmYTUwODI1NDM0ZGZiOGYwMjg5NzBkZGMwYzliZDllZmU3YmQwZmUxZmVjYTk1ZDgx"
		}
		burp0_headers = {
			"Connection": "close", "Cache-Control": "max-age=0",
			"sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
			"sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"",
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
			"Sec-Fetch-Site": "none", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-User": "?1",
			"Sec-Fetch-Dest": "document", "Accept-Encoding": "gzip, deflate",
			"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
		}
		
		response = requests.get(burp0_url, headers=burp0_headers, cookies=burp0_cookies)
		response.close()

		data = json.loads(response.text)
		new_post = data.get('data').get('thread_list')[1]

		title = new_post.get('title')  # 帖子标题
		text = new_post.get('abstract')[0].get('text')  # 内容预览
		link = "https://tieba.baidu.com/p/" + str(new_post.get('id'))  # 链接
		create_time = new_post.get('create_time')  # 创建时间

		if create_time > last_time:
			last_time = create_time
			need_send_message = f'有新帖子\n标题：{title}\n内容：{text}\n链接：{link}'
			self.util.send_group_msg(self.auth, group, need_send_message)

	def timeevent(self):
		schedule.every(2).minutes.do(self.job)

		while True:
			schedule.run_pending()
			time.sleep(1)
