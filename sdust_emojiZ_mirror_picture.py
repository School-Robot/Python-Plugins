"""
图片镜像
"""
import os.path
import os
import uuid
import requests
from PIL import Image

plugin_name = "mirror_picture"
plugin_id = "sdust.emojiZ.mirror_picture"
plugin_version = "1.0.0"
plugin_author = "Z"
plugin_desc = "图片镜像"


class Plugin(object):
    plugin_methods = {'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
                      'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
                      'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
                      'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
                      'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'}}
    plugin_commands = {}
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
        if raw_message.startswith("[CQ:reply,id=") and "镜像" in raw_message:
            target_message_id = raw_message.replace("[CQ:reply,id=", "")[:-3]
            flag, data = self.util.get_msg(self.auth, target_message_id)
            if flag:
                target_message = data['message'][0]
                if target_message['type'] == "image":
                    image_url = target_message['data']['url']
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        temp_dir = os.path.join(self.dir, 'tmp')
                        os.makedirs(temp_dir, exist_ok=True)
                        image_name = f"{uuid.uuid4()}.jpg"
                        save_path = os.path.join(temp_dir, image_name)
                        with open(save_path, 'wb') as file:
                            file.write(response.content)
                        self.log.info(f"图片已保存到: {save_path}")
                        final_path = self.mirror_image(save_path)
                        send_by_cq = self.util.cq_image(file=final_path, type="")
                        self.util.send_group_msg(self.auth, group_id, send_by_cq)
                    else:
                        self.log.error(f"下载失败，状态码: {response.status_code}")

                else:
                    return False
            else:
                self.util.send_group_msg(self.auth, group_id, "发送错误,请重试")
                return False
    def mirror_image(self, path):
        img = Image.open(path)
        base, ext = os.path.splitext(path)
        final_path = base + '_flipped' + ext
        mirror_img = img.transpose(Image.FLIP_LEFT_RIGHT)  # 水平镜像
        mirror_img.save(final_path)
        return final_path
