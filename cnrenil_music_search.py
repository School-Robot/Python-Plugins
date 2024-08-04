import json
import os
import tempfile
import hashlib
import requests

class Plugin(object):
    plugin_methods = {
        'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
        'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
        'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
        'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
        'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'}
    }
    plugin_commands = {
        'music_search': 'music_search_command',
        'help': 'music_search set中的音乐搜索为music_search',
    }
    plugin_auths = {'send_group_msg', 'delete_msg'}
    auth = ''
    log = None
    status = None
    bot = None
    util = None
    dir = None
    stop = False
    config_path = 'config.json'
    config = {
        'manager': 0,
        'cmd': {
            'admin': '/音乐搜索',
            'netease': '/网易云音乐',
            'qq': '/QQ音乐'
        },
        'disabled': []  # Ensure 'disabled' key is initialized
    }
    engine = None
    session = None

    def register(self, logger, util, bot, dir):
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        self.config_path = os.path.join(self.dir, 'config.json')
        self.load_config()
        if self.config['manager']==0:
            self.log.warning("未设置管理员，在控制台使用music_search set <管理员QQ号> 命令设置管理员")
        self.log.info("Plugin register")
        self.clear_temp_cache()

    def enable(self, auth):
        self.auth = auth
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        try:
            self.clear_temp_cache()
        except Exception as e:
            self.log.error(f"Error during cleanup: {e}")
        self.save_config()
        self.log.info("Plugin unregister")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender):
        if raw_message.startswith(self.config['cmd']['admin']):
            if user_id == self.config['manager']:
                if group_id in self.config['disabled']:
                    self.config['disabled'].remove(group_id)
                    self.util.send_group_msg(self.auth, group_id, "音乐插件已启用")
                else:
                    self.config['disabled'].append(group_id)
                    self.util.send_group_msg(self.auth, group_id, "音乐插件已禁用")

            else:
                self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": "无权限"}})
            return True

        if group_id in self.config['disabled']:
            return False

        cache_key = self.get_cache_key(group_id, user_id)
        cached_data = self.load_from_cache(cache_key)

        if raw_message.startswith(self.config['cmd']['netease']) or raw_message.startswith(self.config['cmd']['qq']):
            cmd_parts = raw_message.split(' ', 1)
            if len(cmd_parts) == 1:
                # 没有额外参数，维持原有逻辑
                if not cached_data:
                    self.save_to_cache(cache_key, {'stage': 'waiting_for_music_name', 'is_netease': raw_message.startswith(self.config['cmd']['netease'])})
                    self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": "请输入音乐名称"}})
                    return True
            else:
                # 直接处理搜索请求
                music_name = cmd_parts[1].strip()
                is_netease = raw_message.startswith(self.config['cmd']['netease'])
                search_results = self.search_music(music_name, is_netease)
                self.handle_search_results(search_results, group_id, cache_key, is_netease, time, user_id)
                return True

        if cached_data:
            if cached_data['stage'] == 'waiting_for_music_name':
                music_name = raw_message
                search_results = self.search_music(music_name, cached_data['is_netease'])
                self.handle_search_results(search_results, group_id, cache_key, cached_data['is_netease'], time, user_id)
                return True

            if cached_data['stage'] == 'waiting_for_format_selection':
                if raw_message.split()[0].isdigit() and len(raw_message.split()) == 2:
                    index, format_type = raw_message.split()
                    index = int(index) - 1
                    music_list = cached_data['search_results']
                    if 0 <= index < len(music_list):
                        music = music_list[index]
                        if format_type == "封面":
                            image_url = music['pic']
                            self.util.send_group_msg(self.auth, group_id, {"type": "image", "data": {"file": image_url, "timeout": 30, "cache": 0}})
                            self.util.delete_msg(self.auth, cached_data['message_id'])
                        elif format_type == "链接":
                            self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": music['url']}})
                            self.util.delete_msg(self.auth, cached_data['message_id'])
                        elif format_type == "歌词":
                            self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": music['lrc']}})
                            self.util.delete_msg(self.auth, cached_data['message_id'])
                        elif format_type == "歌词图片":
                            server = "netease" if cached_data['is_netease'] else "tencent"
                            lrc_image_url = f"https://music.renil.cc/?auth=V61TFH9RfxW8VSNM&server={server}&type=BotImage&id={music['id']}"
                            self.util.send_group_msg(self.auth, group_id, {"type": "image", "data": {"file": lrc_image_url, "timeout": 30, "cache": 0}})
                            self.util.delete_msg(self.auth, cached_data['message_id'])
                        elif format_type == "语音":
                            self.util.send_group_msg(self.auth, group_id, {"type": "record", "data": {"file": music['url']}})
                            self.util.delete_msg(self.auth, cached_data['message_id'])
                        else:
                            self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": "无效的格式类型，请重新输入。"}})
                            return True
                        self.delete_cache(cache_key)
                    else:
                        self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": "无效的序号"}})
                else:
                    self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": "输入格式错误，请重新输入"}})
                return True

        return False

    def handle_search_results(self, search_results, group_id, cache_key, is_netease, time, user_id):
        if search_results:
            response_msg = ""
            for idx, music in enumerate(search_results):
                response_msg += f"{idx + 1} - {music['name']} - {music['artist']}\n"
            response_msg += "请输入序号和发送格式类型，比如：1 封面、1 链接、1 歌词、1 歌词图片、1 语音"
            success, ret_data = self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": response_msg}})
            if success:
                message_id = ret_data['message_id']
                self.save_to_cache(cache_key, {
                    'stage': 'waiting_for_format_selection',
                    'music_name': search_results[0]['name'],
                    'search_results': search_results,
                    'is_netease': is_netease,
                    'message_id': message_id,
                    'time': time,
                    'user_id': user_id
                })
        else:
            self.util.send_group_msg(self.auth, group_id, {"type": "text", "data": {"text": "未找到相关音乐"}})

    def search_music(self, music_name, is_netease):
        server = "netease" if is_netease else "tencent"
        api_url = f"https://music.renil.cc/?auth=V61TFH9RfxW8VSNM&server={server}&type=search&id={music_name}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.log.error(f"Error fetching music data: {e}")
            return []

    def save_to_cache(self, key, data):
        temp_dir = tempfile.gettempdir()
        cache_path = os.path.join(temp_dir, f"{key}.json")
        try:
            with open(cache_path, 'w') as cache_file:
                json.dump(data, cache_file)
        except IOError as e:
            self.log.error(f"Error saving cache: {e}")

    def load_from_cache(self, key):
        temp_dir = tempfile.gettempdir()
        cache_path = os.path.join(temp_dir, f"{key}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as cache_file:
                    return json.load(cache_file)
            except (IOError, json.JSONDecodeError) as e:
                self.log.error(f"Error loading cache: {e}")
        return None

    def delete_cache(self, key):
        temp_dir = tempfile.gettempdir()
        cache_path = os.path.join(temp_dir, f"{key}.json")
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except IOError as e:
                self.log.error(f"Error deleting cache: {e}")

    def get_cache_key(self, group_id, user_id):
        hash_input = f"{group_id}_{user_id}".encode('utf-8')
        return hashlib.md5(hash_input).hexdigest()

    def clear_temp_cache(self):
        temp_dir = tempfile.gettempdir()
        for file in os.listdir(temp_dir):
            if file.endswith(".json"):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except IOError as e:
                    self.log.error(f"Error clearing temp cache: {e}")

    def music_search_command(self, cmd):
        if len(cmd) == 2:
            if cmd[0] == 'set':
                try:
                    self.config['manager'] = int(cmd[1])
                    self.save_config()
                    self.log.info('设置成功')
                except ValueError:
                    self.log.warning('参数错误')
            else:
                self.log.warning('参数错误')
        else:
            self.log.warning('参数错误')

    def save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f)
        except IOError as e:
            self.log.error(f"Error saving config: {e}")

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                self.log.error(f"Error loading config: {e}")
        else:
            # Write default config if file does not exist
            try:
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f)
                self.log.info('配置文件不存在，已创建默认配置')
            except IOError as e:
                self.log.error(f"Error creating default config: {e}")

plugin_name = "音乐搜索插件"
plugin_id = "cc.renil.music_search"
plugin_version = "1.0.0"
plugin_author = "cnrenil和gpt"
plugin_desc = "网易云和QQ音乐搜索回复插件"

