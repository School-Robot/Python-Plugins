def handle_level_command(self, message_id, group_id, user_id, raw_message):
    parts = raw_message.split()
    if len(parts) == 2:  # Only "#addc level"
        level = self.word_manager.get_admin_level(user_id)
        return True, self.util.cq_reply(message_id) + f"您当前的权限等级是：{level}"
    elif len(parts) == 4:  # "#addc level QQ号 等级"
        return set_admin_level(self,message_id, group_id, user_id, raw_message)
    else:
        return True, self.util.cq_reply(message_id) + "格式错误，正确格式：#addc level 或 #addc level QQ号 等级"

def set_admin_level(self, message_id, group_id, user_id, raw_message):
    if not self.word_manager.is_super_admin(user_id):
        return True, self.util.cq_reply(message_id) + "您没有权限设置管理员等级"
    parts = raw_message.split()
    if len(parts) != 4:
        return True, self.util.cq_reply(message_id) + "格式错误，正确格式：#addc level QQ号 等级(1-5)"
    admin_qq, level = parts[2], int(parts[3])
    if level < 1 or level > 5:
        return True, self.util.cq_reply(message_id) + "等级必须在1-5之间"
    self.word_manager.add_admin(admin_qq, level)
    return True, self.util.cq_reply(message_id) + f"管理员{admin_qq}的等级已设置为{level}"

def get_all_commands_help(self, user_id):
    is_admin = self.word_manager.get_admin_level(user_id) > 0
    is_super_admin = self.word_manager.is_super_admin(user_id)

    help_text = "词条管理系统命令列表：\n"
    help_text += "#add 问题 答案 - 添加新词条\n"
    help_text += "#addc query 关键词 - 搜索词条\n"
    help_text += "#addc requery 正则表达式 - 使用正则表达式搜索词条\n"
    help_text += "#show_all - 显示所有词条\n"
    help_text += "#addc level - 显示当前用户的权限等级\n"
    
    if is_admin:
        help_text += "#addc del 问题 - 删除词条\n"
    
    if is_super_admin:
        help_text += "#addc admin QQ号 - 添加管理员\n"
        help_text += "#addc level QQ号 等级 - 设置管理员等级（1-5）\n"
    
    help_text += "#addc help [命令] - 显示帮助信息或特定命令的详细帮助\n"
    help_text += "\n使用 '#addc help 命令名' 可以查看特定命令的详细说明。"
    
    return help_text

def get_command_help(self, command, user_id):
    is_admin = self.word_manager.get_admin_level(user_id) > 0
    is_super_admin = self.word_manager.is_super_admin(user_id)

    help_dict = {
        "add": "添加新词条\n用法：#add 问题 答案\n说明：添加一个新的问答对到词条库中。答案可以包含文字和图片。",
        "query": "搜索词条\n用法：#addc query 关键词\n说明：搜索包含指定关键词的所有词条。",
        "requery": "使用正则表达式搜索词条\n用法：#addc requery 正则表达式\n说明：使用正则表达式搜索匹配的词条。",
        "show_all": "显示所有词条\n用法：#show_all\n说明：显示当前群组中的所有词条。",
        "level": "显示或设置权限等级\n用法：#addc level [QQ号 等级]\n说明：不带参数时显示当前用户的权限等级，带参数时设置指定用户的权限等级（需要超级管理员权限）。",
        "del": "删除词条（需要管理员权限）\n用法：#addc del 问题\n说明：删除指定问题的词条。",
        "admin": "添加管理员（需要超级管理员权限）\n用法：#addc admin QQ号\n说明：将指定QQ号添加为管理员。",
        "help": "显示帮助信息\n用法：#addc help [命令]\n说明：显示所有可用命令或特定命令的详细帮助。"
    }

    if command not in help_dict:
        return f"未找到命令 '{command}' 的帮助信息。请使用 '#addc help' 查看所有可用命令。"

    if (command in ["del"] and not is_admin) or (command in ["admin", "level"] and not is_super_admin):
        return f"您没有使用 '{command}' 命令的权限。"

    return help_dict[command]