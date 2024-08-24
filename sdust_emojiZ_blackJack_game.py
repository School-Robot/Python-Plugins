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
        self.developer_user_id = "291875783"
        self.play_info = {}
        self.max_player_at_same_time = 3
        self.log.info("Plugin register")

    def enable(self, auth):
        self.auth = auth
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.log.info("Plugin unregister")
        self.play_info = {}

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message,
                      font, sender):
        if raw_message == "21点":
            base_cards = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8,
                          8, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
            if len(self.play_info) == self.max_player_at_same_time:
                self.util.send_group_msg(self.auth, group_id, "同时参与玩家数达到上限，请稍后再试")
                return False
            system_get_card_index = random.randint(0, len(base_cards) - 1)
            system_get_card_num = base_cards[system_get_card_index]
            del base_cards[system_get_card_index]
            user_get_card_index = random.randint(0, len(base_cards) - 1)
            user_get_card_num = base_cards[user_get_card_index]
            del base_cards[user_get_card_index]
            self.play_info[str(user_id)] = {"user_cards": [system_get_card_num], "system_cards": [user_get_card_num],
                                            "row": 1, "left_card": base_cards}
            need_send = f"第{str(self.play_info[str(user_id)]['row'])}轮发牌结束:\n" \
                        f"当前用户手牌为:{self.play_info[str(user_id)]['user_cards']}\n" \
                        f"庄家手牌为:{self.play_info[str(user_id)]['system_cards']}\n" \
                        f"当前用户手牌点数和为:{sum(self.play_info[str(user_id)]['user_cards'])}\n" \
                        f"当前庄家手牌点数和为:{sum(self.play_info[str(user_id)]['system_cards'])}\n" \
                        f"当前轮数为:{self.play_info[str(user_id)]['row']}\n" \
                        f"如要继续拿牌请发送\"拿牌\",否则请发送\"结束游戏\""
            need_send = self.util.cq_reply(id=message_id) + need_send
            self.util.send_group_msg(self.auth, group_id, need_send)
            return True
        if raw_message == "拿牌":
            if str(user_id) not in self.play_info.keys():
                self.util.send_group_msg(self.auth, group_id, "你尚未开始一局游戏，请发送 \"21点\" 开始一把牌局")
                return False
            else:
                now_user_cards = list(self.play_info[str(user_id)]['user_cards'])
                now_cards = self.play_info[str(user_id)]["left_card"]
                user_get_card_index = random.randint(0, len(now_cards) - 1)
                user_get_card_num = now_cards[user_get_card_index]
                now_user_cards.append(user_get_card_num)
                del now_cards[user_get_card_index]
                self.play_info[str(user_id)]['user_cards'] = now_user_cards
                self.play_info[str(user_id)]['row'] = self.play_info[str(user_id)]['row'] + 1
                self.play_info[str(user_id)]["left_card"] = now_cards

                if sum(self.play_info[str(user_id)]['user_cards']) > 21:
                    self.util.send_group_msg(self.auth, group_id,
                                             f"{self.util.cq_reply(id=message_id)}"
                                             f"用户和{sum(self.play_info[str(user_id)]['user_cards'])}点爆牌,"
                                             f"庄家胜")
                    if str(user_id) != self.developer_user_id:
                        self.util.set_group_ban(self.auth, group_id, user_id, 60)
                    del self.play_info[str(user_id)]
                    return True
                else:
                    need_send = f"第{str(self.play_info[str(user_id)]['row'])}轮发牌结束:\n" \
                                f"当前用户手牌为:{self.play_info[str(user_id)]['user_cards']}\n" \
                                f"庄家手牌为:{self.play_info[str(user_id)]['system_cards']}\n" \
                                f"当前用户手牌点数和为:{sum(self.play_info[str(user_id)]['user_cards'])}\n" \
                                f"当前庄家手牌点数和为:{sum(self.play_info[str(user_id)]['system_cards'])}\n" \
                                f"当前轮数为:{self.play_info[str(user_id)]['row']}\n" \
                                f"如要继续拿牌请发送\"拿牌\",否则请发送\"结束游戏\""
                    need_send = self.util.cq_reply(id=message_id) + need_send
                    self.util.send_group_msg(self.auth, group_id, need_send)
                return True

        if raw_message == "结束游戏":
            if str(user_id) not in self.play_info.keys():
                self.util.send_group_msg(self.auth, group_id, "你尚未开始一局游戏，请发送 \"21点\" 开始一把牌局")
                return False
            while sum(self.play_info[str(user_id)]['system_cards']) <= 16:
                if sum(self.play_info[str(user_id)]['system_cards']) > 17:
                    break
                self.play_info[str(user_id)]['row'] = self.play_info[str(user_id)]['row'] + 1
                now_system_cards = list(self.play_info[str(user_id)]['system_cards'])
                now_cards = self.play_info[str(user_id)]["left_card"]
                system_get_card_index = random.randint(0, len(now_cards) - 1)
                system_get_card_num = now_cards[system_get_card_index]
                now_system_cards.append(system_get_card_num)
                self.play_info[str(user_id)]['system_cards'] = now_system_cards
                del now_cards[system_get_card_index]
                need_send = f"第{str(self.play_info[str(user_id)]['row'])}轮发牌结束:\n" \
                            f"当前用户手牌为:{self.play_info[str(user_id)]['user_cards']}\n" \
                            f"当前庄家手牌为:{self.play_info[str(user_id)]['system_cards']}\n" \
                            f"当前用户手牌点数和为:{sum(self.play_info[str(user_id)]['user_cards'])}\n" \
                            f"当前庄家手牌点数和为:{sum(self.play_info[str(user_id)]['system_cards'])}\n" \
                            f"当前轮数为:{self.play_info[str(user_id)]['row']}\n"
                if sum(self.play_info[str(user_id)]['system_cards']) > 21:
                    need_send = self.util.cq_reply(
                        id=message_id) + need_send + "\n" + f"庄家和:{sum(self.play_info[str(user_id)]['system_cards'])}点爆牌" \
                                                            f"玩家胜"
                    self.util.send_msg(self.auth, group_id, need_send)
                    del self.play_info[str(user_id)]
                    return True
                self.util.send_group_msg(self.auth, group_id, f"{self.util.cq_reply(id=message_id) + need_send}")
            if sum(self.play_info[str(user_id)]['user_cards']) > sum(self.play_info[str(user_id)]['system_cards']):
                need_send = f"当前用户手牌为:{self.play_info[str(user_id)]['user_cards']}\n当前庄家手牌为:{self.play_info[str(user_id)]['system_cards']}\n当前用户手牌点数和为:{sum(self.play_info[str(user_id)]['user_cards'])}\n当前庄家手牌点数和为:{sum(self.play_info[str(user_id)]['system_cards'])}\n用户胜利"
            else:
                need_send = f"当前用户手牌为:{self.play_info[str(user_id)]['user_cards']}\n当前庄家手牌为:{self.play_info[str(user_id)]['system_cards']}\n当前用户手牌点数和为:{sum(self.play_info[str(user_id)]['user_cards'])}\n当前庄家手牌点数和为:{sum(self.play_info[str(user_id)]['system_cards'])}\n庄家胜利"
                if str(user_id) != self.developer_user_id:
                    self.util.set_group_ban(self.auth, group_id, user_id, 60)
            need_send = self.util.cq_reply(id=message_id) + need_send
            self.util.send_group_msg(self.auth, group_id, need_send)
            del self.play_info[str(user_id)]
            return True
        return False
