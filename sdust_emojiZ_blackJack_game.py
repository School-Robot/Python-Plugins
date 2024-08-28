import random

plugin_name = "blackjack_game"
plugin_id = "sdust.emojiZ.BlackJack_game"
plugin_version = "1.0.1"
plugin_author = "Z"
plugin_desc = "21点游戏"


# TODO 多人模式
# TODO 对接用户系统金币开局

class Plugin(object):
    plugin_methods = {'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
                      'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
                      'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
                      'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
                      'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'}}
    plugin_commands = {}
    plugin_auths = {'send_group_msg', 'set_group_ban'}
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
        self.base_cards = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8,
                           8, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        self.developer_user_id = "291875783"
        self.single_play_info = {}  # 单人对局信息
        self.mutile_play_info = {}  # 多人对局信息
        self.max_player_at_same_time = 10  # 同时最大局数 单人+多人
        self.log.info("Plugin register")

    def enable(self, auth):
        self.auth = auth
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.log.info("Plugin unregister")
        self.single_play_info = {}
        self.mutile_play_info = {}

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message,
                      font, sender):
        process_flag = False
        if raw_message == "21点多人" or raw_message == "拿牌多人" or raw_message.startswith("加入游戏") or raw_message == "撤销游戏":
            process_flag = self.play_with_other(message_id, group_id, user_id, raw_message)
        elif raw_message == "21点" or raw_message == "拿牌":
            process_flag = self.play_with_system(message_id, group_id, user_id, raw_message)
        return process_flag

    def get_all_follower(self):
        """
        获取当前所有闲家的QQ号，避免同时当庄和闲
        """
        all_followers = []
        for key in self.mutile_play_info.keys():
            follower_user_id = str(self.mutile_play_info[key]["follower"])
            if follower_user_id != "":
                all_followers.append(follower_user_id)
        return list(set(all_followers))

    def check_if_can_do_master(self, user_id):
        """
        检查该用户是否可以坐庄
        """
        check_flag = True
        check_info = "你已创建一局21点游戏，请等待他人发送\'加入游戏@xxxx\'来加入对局"
        all_followers = self.get_all_follower()
        if str(user_id) in self.single_play_info.keys():
            check_info = "你不可以同时与进行多局游戏"
            check_flag = False
            return check_flag, check_info
        if str(user_id) in self.mutile_play_info.keys():
            check_info = "你不可以同时与进行多局游戏"
            check_flag = False
            return check_flag, check_info
        if str(user_id) in all_followers:
            check_info = "你不可以同时与进行多局游戏"
            check_flag = False
            return check_flag, check_info
        if len(self.single_play_info) + len(self.mutile_play_info) == self.max_player_at_same_time:  # 最大对局超限
            check_info = "超过最大对局数限制,请稍候"
            check_flag = False
            return check_flag, check_info
        return check_flag, check_info

    def check_can_follow(self, user_id, raw_message):
        """
        检查玩家是否可以加入某个庄家的牌局
        """
        follow_flag = True
        follow_info = ""
        master = raw_message.replace("加入游戏[CQ:at,qq=", "")[:-1]  # 尝试加入对局的庄家
        now_follower = self.get_all_follower()  # 当前所有闲家
        now_master = self.mutile_play_info.keys()  # 当前所有庄家
        now_singler = self.single_play_info.keys()  # 当前所有跟系统玩的人
        if str(user_id) in now_master or str(user_id) in now_singler or str(user_id) in now_follower:  # 你不能同时玩多局
            follow_flag = False
            follow_info = "你不可以同时进行多局游戏"
            return follow_flag, follow_info
        if master not in self.mutile_play_info.keys():  # 艾特这个人没有牌局
            follow_flag = False
            follow_info = "庄家不存在"
            return follow_flag, follow_info
        if self.mutile_play_info[str(master)]["follower"] != "":  # 艾特这个人的牌局已被他人加入
            follow_flag = False
            follow_info = "该对局人数已满"
            return follow_flag, follow_info
        return follow_flag, follow_info

    def check_can_drawback(self, user_id):
        """
        检查庄家是否可以撤销对局
        """
        drawback_flag = True
        drawback_info = ""
        if str(user_id) not in self.mutile_play_info.keys():  # 当前用户不是庄家 无需撤销
            drawback_flag = False
            drawback_info = "你并未坐庄,无需撤销对局"
            return drawback_flag, drawback_info
        if self.mutile_play_info[str(user_id)]['follower'] != "":  # 对局已开始,无法毁局
            drawback_flag = False
            drawback_info = "对局已开始，愿赌服输，无法撤销"
            return drawback_flag, drawback_info
        return drawback_flag, drawback_info

    def play_with_other(self, message_id, group_id, user_id, raw_message):
        if raw_message == "21点多人":  # 多人模式坐庄
            check_flag, check_info = self.check_if_can_do_master(user_id)
            if not check_flag:
                need_send = self.util.cq_reply(id=message_id) + check_info
                self.util.send_group_msg(self.auth, group_id, need_send)
            else:
                self.mutile_play_info[str(user_id)] = {"master": str(user_id), "follower": ""}
                need_send = self.util.cq_reply(id=message_id) + check_info
                self.util.send_group_msg(self.auth, group_id, need_send)
            return True
        if raw_message.startswith("加入游戏[CQ:at,qq="):  # 加入游戏逻辑
            follow_check_flag, follow_check_info = self.check_can_follow(user_id, raw_message)
            if not follow_check_flag:
                need_send = self.util.cq_reply(id=message_id) + follow_check_info
                self.util.send_group_msg(self.auth, group_id, need_send)
            else:
                master = raw_message.replace("加入游戏[CQ:at,qq=", "")[:-1]  # 找到该桌子庄家
                self.mutile_play_info[str(master)]["follower"] = str(user_id)  # 记录该桌闲家
                self.single_play_info[str(master)]['master_cards'] = []
                self.single_play_info[str(master)]['follower_cards'] = []
                self.mutile_play_info[str(master)]['left_cards'] = self.base_cards
                need_send = self.util.cq_at(qq=master) + self.util.cq_at(qq=str(user_id)) + \
                            f"双方已加入游戏,请闲家{self.util.cq_at(qq=str(user_id))}" \
                            f"发送\'拿牌多人\'拿牌或发送\'停牌多人结束游戏\'"
                self.util.send_group_msg(self.auth, group_id, need_send)
            return True
        if raw_message == "拿牌多人":
            # TODO 多人拿牌逻辑 闲家先拿到停牌
            pass
        if raw_message == "撤销游戏":  # 长时间无闲家加入,庄家撤销游戏
            drawback_flag, drawback_info = self.check_can_drawback(user_id)
            if not drawback_flag:
                need_send = self.util.cq_reply(id=message_id) + drawback_info
                self.util.send_group_msg(self.auth, group_id, need_send)
            else:
                del self.mutile_play_info[str(user_id)]
                self.util.send_group_msg(self.auth, group_id, "对局已撤销")
            return True
        return False

    def play_with_system(self, message_id, group_id, user_id, raw_message):
        """
        和系统玩
        """
        if raw_message == "21点":
            base_cards = self.base_cards
            if len(self.single_play_info) == self.max_player_at_same_time:
                self.util.send_group_msg(self.auth, group_id, "同时参与玩家数达到上限，请稍后再试")
                return False
            system_get_card_index = random.randint(0, len(base_cards) - 1)
            system_get_card_num = base_cards[system_get_card_index]
            del base_cards[system_get_card_index]
            user_get_card_index = random.randint(0, len(base_cards) - 1)
            user_get_card_num = base_cards[user_get_card_index]
            del base_cards[user_get_card_index]
            self.single_play_info[str(user_id)] = {"user_cards": [system_get_card_num],
                                                   "system_cards": [user_get_card_num],
                                                   "row": 1, "left_card": base_cards}
            need_send = f"第{str(self.single_play_info[str(user_id)]['row'])}轮发牌结束:\n" \
                        f"当前用户手牌为:{self.single_play_info[str(user_id)]['user_cards']}\n" \
                        f"庄家手牌为:{self.single_play_info[str(user_id)]['system_cards']}\n" \
                        f"当前用户手牌点数和为:{sum(self.single_play_info[str(user_id)]['user_cards'])}\n" \
                        f"当前庄家手牌点数和为:{sum(self.single_play_info[str(user_id)]['system_cards'])}\n" \
                        f"当前轮数为:{self.single_play_info[str(user_id)]['row']}\n" \
                        f"如要继续拿牌请发送\"拿牌\",否则请发送\"结束游戏\""
            need_send = self.util.cq_reply(id=message_id) + need_send
            self.util.send_group_msg(self.auth, group_id, need_send)
            return True
        if raw_message == "拿牌":
            if str(user_id) not in self.single_play_info.keys():
                self.util.send_group_msg(self.auth, group_id, "你尚未开始一局游戏，请发送 \"21点\" 开始一把牌局")
                return False
            else:
                now_user_cards = list(self.single_play_info[str(user_id)]['user_cards'])
                now_cards = self.single_play_info[str(user_id)]["left_card"]
                user_get_card_index = random.randint(0, len(now_cards) - 1)
                user_get_card_num = now_cards[user_get_card_index]
                now_user_cards.append(user_get_card_num)
                del now_cards[user_get_card_index]
                self.single_play_info[str(user_id)]['user_cards'] = now_user_cards
                self.single_play_info[str(user_id)]['row'] = self.single_play_info[str(user_id)]['row'] + 1
                self.single_play_info[str(user_id)]["left_card"] = now_cards

                if sum(self.single_play_info[str(user_id)]['user_cards']) > 21:
                    self.util.send_group_msg(self.auth, group_id,
                                             f"{self.util.cq_reply(id=message_id)}"
                                             f"用户和{sum(self.single_play_info[str(user_id)]['user_cards'])}点爆牌,"
                                             f"庄家胜")
                    if str(user_id) != self.developer_user_id:
                        self.util.set_group_ban(self.auth, group_id, user_id, 60)
                    del self.single_play_info[str(user_id)]
                    return True
                else:
                    need_send = f"第{str(self.single_play_info[str(user_id)]['row'])}轮发牌结束:\n" \
                                f"当前用户手牌为:{self.single_play_info[str(user_id)]['user_cards']}\n" \
                                f"庄家手牌为:{self.single_play_info[str(user_id)]['system_cards']}\n" \
                                f"当前用户手牌点数和为:{sum(self.single_play_info[str(user_id)]['user_cards'])}\n" \
                                f"当前庄家手牌点数和为:{sum(self.single_play_info[str(user_id)]['system_cards'])}\n" \
                                f"当前轮数为:{self.single_play_info[str(user_id)]['row']}\n" \
                                f"如要继续拿牌请发送\"拿牌\",否则请发送\"结束游戏\""
                    need_send = self.util.cq_reply(id=message_id) + need_send
                    self.util.send_group_msg(self.auth, group_id, need_send)
                return True

        if raw_message == "结束游戏":
            if str(user_id) not in self.single_play_info.keys():
                self.util.send_group_msg(self.auth, group_id, "你尚未开始一局游戏，请发送 \"21点\" 开始一把牌局")
                return False
            while sum(self.single_play_info[str(user_id)]['system_cards']) <= 16:
                if sum(self.single_play_info[str(user_id)]['system_cards']) > 17:
                    break
                self.single_play_info[str(user_id)]['row'] = self.single_play_info[str(user_id)]['row'] + 1
                now_system_cards = list(self.single_play_info[str(user_id)]['system_cards'])
                now_cards = self.single_play_info[str(user_id)]["left_card"]
                system_get_card_index = random.randint(0, len(now_cards) - 1)
                system_get_card_num = now_cards[system_get_card_index]
                now_system_cards.append(system_get_card_num)
                self.single_play_info[str(user_id)]['system_cards'] = now_system_cards
                del now_cards[system_get_card_index]
                need_send = f"第{str(self.single_play_info[str(user_id)]['row'])}轮发牌结束:\n" \
                            f"当前用户手牌为:{self.single_play_info[str(user_id)]['user_cards']}\n" \
                            f"当前庄家手牌为:{self.single_play_info[str(user_id)]['system_cards']}\n" \
                            f"当前用户手牌点数和为:{sum(self.single_play_info[str(user_id)]['user_cards'])}\n" \
                            f"当前庄家手牌点数和为:{sum(self.single_play_info[str(user_id)]['system_cards'])}\n" \
                            f"当前轮数为:{self.single_play_info[str(user_id)]['row']}\n"
                if sum(self.single_play_info[str(user_id)]['system_cards']) > 21:
                    need_send = self.util.cq_reply(
                        id=message_id) + need_send + "\n" + f"庄家和:{sum(self.single_play_info[str(user_id)]['system_cards'])}点爆牌" \
                                                            f"玩家胜"
                    self.util.send_group_msg(self.auth, group_id, need_send
                    del self.single_play_info[str(user_id)]
                    del self.play_info[str(user_id)]
                    return True
                self.util.send_group_msg(self.auth, group_id, f"{self.util.cq_reply(id=message_id) + need_send}")
            if sum(self.single_play_info[str(user_id)]['user_cards']) > sum(
                    self.single_play_info[str(user_id)]['system_cards']):
                need_send = f"当前用户手牌为:{self.single_play_info[str(user_id)]['user_cards']}\n当前庄家手牌为:{self.single_play_info[str(user_id)]['system_cards']}\n当前用户手牌点数和为:{sum(self.single_play_info[str(user_id)]['user_cards'])}\n当前庄家手牌点数和为:{sum(self.single_play_info[str(user_id)]['system_cards'])}\n用户胜利"
            else:
                need_send = f"当前用户手牌为:{self.single_play_info[str(user_id)]['user_cards']}\n当前庄家手牌为:{self.single_play_info[str(user_id)]['system_cards']}\n当前用户手牌点数和为:{sum(self.single_play_info[str(user_id)]['user_cards'])}\n当前庄家手牌点数和为:{sum(self.single_play_info[str(user_id)]['system_cards'])}\n庄家胜利"
                if str(user_id) != self.developer_user_id:
                    self.util.set_group_ban(self.auth, group_id, user_id, 60)
            need_send = self.util.cq_reply(id=message_id) + need_send
            self.util.send_group_msg(self.auth, group_id, need_send)
            del self.single_play_info[str(user_id)]
            return True
        return False
