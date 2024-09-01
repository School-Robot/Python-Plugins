# commands.py

from .man import *
import re
from .info import plugin_version



def handle_reply(self, message_id, response):
    if message_id is not None:
        return self.util.cq_reply(message_id) + response
    return response


def add_word(self, message_id, group_id, user_id, message, message_json):
    """
    添加词条
    """
    if self.word_manager.get_admin_level(user_id) <= 0:
        return True, handle_reply(self, message_id, "您没有权限添加词条")

    parts = message.split(" ", 2)
    if len(parts) != 3:
        return True, handle_reply(self, message_id, "格式错误，正确格式：#add 问题 答案")
    
    question, answer = parts[1], parts[2]
    
    try:
        self.word_manager.add_word(group_id, question, answer, message_json)
        return True, handle_reply(self, message_id, f"词条'{question}'添加成功")
    except Exception as e:
        error_msg = f"添加词条失败：{str(e)}"
        print(error_msg)
        return True, handle_reply(self, message_id, error_msg)

def show_all_answers(self, message_id, group_id, user_id, raw_message):
    question = raw_message.split(" ", 2)[2]
    answers = self.word_manager.get_all_answers(group_id, question)
    if not answers:
        return True, handle_reply(self, message_id, f"未找到问题 '{question}' 的回答")
    
    reply = f"问题 '{question}' 的所有回答：\n"
    for i, answer in enumerate(answers, 1):
        reply += f"{i}. {answer}\n"
    
    return True, handle_reply(self, message_id, reply.strip())

def show_all_alias_definitions(self, message_id, group_id, user_id, raw_message):
    alias = raw_message.split(" ", 2)[2]
    definitions = self.word_manager.get_all_alias_definitions(group_id, alias)
    if not definitions:
        return True, handle_reply(self, message_id, f"未找到别名 '{alias}' 的定义")
    
    reply = f"别名 '{alias}' 的所有定义：\n"
    for i, definition in enumerate(definitions, 1):
        reply += f"{i}. {definition}\n"
    
    return True, handle_reply(self, message_id, reply.strip())

def delete_word(self, message_id, group_id, user_id, raw_message):
    if self.word_manager.get_admin_level(user_id) < 1:
        return True, handle_reply(self, message_id, "您没有权限删除词条")
    question = raw_message.split(" ", 2)[2]
    self.word_manager.delete_word(group_id, question)
    return True, handle_reply(self, message_id, f"词条'{question}'已删除")

def query_word(self, message_id, group_id, user_id, raw_message):
    keyword = raw_message.split(" ", 2)[2]
    results = self.word_manager.search_words(group_id, keyword)
    if not results:
        return True, handle_reply(self, message_id, "未找到匹配的词条")
    response = "匹配的词条：\n" + "\n".join([f"问：{q}\n答：{a}" for q, a in results])
    return True, handle_reply(self, message_id, response)

def regex_query_word(self, message_id, group_id, user_id, raw_message):
    pattern = raw_message.split(" ", 2)[2]
    try:
        results = self.word_manager.regex_search(group_id, pattern)
    except re.error:
        return True, handle_reply(self, message_id, "无效的正则表达式")
    if not results:
        return True, handle_reply(self, message_id, "未找到匹配的词条")
    response = "匹配的词条：\n" + "\n".join([f"问：{q}\n答：{a}" for q, a in results])
    return True, handle_reply(self, message_id, response)

def add_admin(self, message_id, group_id, user_id, raw_message):
    if not self.word_manager.is_super_admin(user_id):
        return True, handle_reply(self, message_id, "您没有权限添加管理员")
    parts = raw_message.split(" ")
    if len(parts) != 3:
        return True, handle_reply(self, message_id, "格式错误，正确格式：#addc admin QQ号")
    new_admin_qq = parts[2]
    self.word_manager.add_admin(new_admin_qq, 1)
    return True, handle_reply(self, message_id, f"管理员{new_admin_qq}添加成功")

def handle_level_command(self, message_id, group_id, user_id, raw_message):
    parts = raw_message.split()
    if len(parts) == 2:  # Only "#addc level"
        level = self.word_manager.get_admin_level(user_id)
        return True, handle_reply(self, message_id, f"您当前的权限等级是：{level}")
    elif len(parts) == 4:  # "#addc level QQ号 等级"
        return set_admin_level(self, message_id, group_id, user_id, raw_message)
    else:
        return True, handle_reply(self, message_id, "格式错误，正确格式：#addc level 或 #addc level QQ号 等级")

def set_admin_level(self, message_id, group_id, user_id, raw_message):
    if not self.word_manager.is_super_admin(user_id):
        return True, handle_reply(self, message_id, "您没有权限设置管理员等级")
    parts = raw_message.split()
    if len(parts) != 4:
        return True, handle_reply(self, message_id, "格式错误，正确格式：#addc level QQ号 等级(1-5)")
    admin_qq, level = parts[2], int(parts[3])
    if level < 1 or level > 5:
        return True, handle_reply(self, message_id, "等级必须在1-5之间")
    self.word_manager.add_admin(admin_qq, level)
    return True, handle_reply(self, message_id, f"管理员{admin_qq}的等级已设置为{level}")

def show_all_words(self, message_id, group_id):
    words = self.word_manager.get_all_words(group_id)
    if not words:
        return True, handle_reply(self, message_id, "当前群组没有词条")
    reply = "所有词条：\n"
    for question, answer in words:
        reply += f"问：{question}\n答：{answer}\n\n"
    return True, handle_reply(self, message_id, reply.strip())

def show_help(self, message_id, group_id, user_id, raw_message):
    parts = raw_message.split()
    if len(parts) > 2:
        # 显示特定命令的帮助
        command = parts[2]
        help_text = get_command_help(self, command, user_id)
    else:
        # 显示所有命令的概览
        help_text = get_all_commands_help(self, user_id)
    
    processed_help_text = process_command_references(help_text)
    return True, handle_reply(self, message_id, processed_help_text)

def show_questions(self, message_id, group_id, user_id, raw_message):
    parts = raw_message.split()
    if len(parts) < 4:
        return True, handle_reply(self, message_id, "格式错误，正确格式：#addc show question <id/all> [每行显示的问题数] [是否显示序号]")
    
    question_id = parts[3]
    questions_per_line = 1  # 默认每行显示1个问题
    show_numbers = True  # 默认显示序号
    
    if len(parts) > 4 and question_id == 'all':
        try:
            questions_per_line = int(parts[4])
            if questions_per_line < 1:
                raise ValueError
        except ValueError:
            return True, handle_reply(self, message_id, "每行显示的问题数必须是正整数")

    if len(parts) > 5 and question_id == 'all':
        show_numbers = parts[5].lower() in ['true', 'yes', '1', 'y', 't']

    questions = self.word_manager.get_questions(group_id, question_id)
    
    if not questions:
        return True, handle_reply(self, message_id, "未找到匹配的问题")
    
    reply = "问题列表：\n"
    
    if questions_per_line == 1:
        for id, question in questions:
            if show_numbers:
                reply += f"{id}. {question}\n"
            else:
                reply += f"{question}\n"
    else:
        for i in range(0, len(questions), questions_per_line):
            line = []
            for j in range(questions_per_line):
                if i + j < len(questions):
                    id, question = questions[i + j]
                    if show_numbers:
                        line.append(f"{id}. {question}")
                    else:
                        line.append(question)
            reply += " | ".join(line) + "\n"
    
    return True, handle_reply(self, message_id, reply.strip())

def add_alias(self, message_id, group_id, user_id, raw_message):
    if self.word_manager.get_admin_level(user_id) < 1:
        return True, handle_reply(self, message_id, "您没有权限添加别名")

    # 使用正则表达式来分割命令，保留引号内的空格
    parts = re.split(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', raw_message.strip())
    if len(parts) < 4:
        return True, handle_reply(self, message_id, "格式错误，正确格式：#addc alias add 别名 命令")

    alias = parts[3]
    command = " ".join(parts[4:]).strip('"')  # 移除可能存在的引号
    self.word_manager.add_alias(group_id, alias, command)
    return True, handle_reply(self, message_id, f"别名 '{alias}' 添加成功")

def delete_alias(self, message_id, group_id, user_id, raw_message):
    if self.word_manager.get_admin_level(user_id) < 1:
        return True, handle_reply(self, message_id, "您没有权限删除别名")

    parts = raw_message.split(" ", 3)
    if len(parts) != 4:
        return True, handle_reply(self, message_id, "格式错误，正确格式：#addc alias del 别名")

    alias = parts[3]
    self.word_manager.delete_alias(group_id, alias)
    return True, handle_reply(self, message_id, f"别名 '{alias}' 删除成功")

def list_aliases(self, message_id, group_id):
    aliases = self.word_manager.list_aliases(group_id)
    if not aliases:
        return True, handle_reply(self, message_id, "当前群组没有设置别名")
    
    reply = "当前群组的别名列表：\n"
    for alias, command in aliases:
        reply += f"{alias}: {command}\n"
    return True, handle_reply(self, message_id, reply.strip())

def process_command_references(text):
    def replace_command(match):
        command = match.group(1)
        return f'#addc {command}'

    pattern = r'\$\$<command:(.*?)>\$\$'
    return re.sub(pattern, replace_command, text)



def show_status(self, message_id, group_id, user_id):
    word_count = self.word_manager.get_word_count()
    user_level = self.word_manager.get_admin_level(user_id)
    db_info = self.word_manager.get_database_info()
    pic_size = self.word_manager.get_pic_directory_size()

    status_text = f"系统状态：\n"
    status_text += f"1. 当前数据库词条数量：{word_count}\n"
    status_text += f"2. 当前用户权限等级：{user_level}\n"
    status_text += f"3. 当前连接的数据库：{db_info}\n"
    status_text += f"4. ./pic目录占用大小：{pic_size / (1024*1024):.2f} MB\n"
    status_text += f"5. 插件版本：{plugin_version}\n"

    return True, handle_reply(self, message_id, status_text)
def get_all_commands_help(self, user_id):
    is_admin = self.word_manager.get_admin_level(user_id) > 0
    is_super_admin = self.word_manager.is_super_admin(user_id)

    help_text = "词条管理系统命令列表：\n\n"
    
    # 基础命令
    help_text += "基础命令：\n"
    help_text += "  #add 问题 答案 - 添加新词条\n"
    help_text += "  $$<command:query>$$ 关键词 - 搜索词条\n"
    help_text += "  $$<command:requery>$$ 正则表达式 - 使用正则表达式搜索词条\n"
    help_text += "  #show_all - 显示所有词条\n"
    help_text += "  $$<command:show question>$$ <id/all> [每行显示数] - 显示指定ID或所有问题\n"
    help_text += "  $$<command:show_answers>$$ 问题 - 显示指定问题的所有答案\n"
    help_text += "  $$<command:help>$$ [命令] - 显示帮助信息或特定命令的详细帮助\n\n"
    
    # 别名命令
    help_text += "别名命令：\n"
    help_text += "  $$<command:alias add>$$ 别名 命令 - 添加命令别名\n"
    help_text += "  $$<command:alias del>$$ 别名 - 删除命令别名\n"
    help_text += "  $$<command:alias list>$$ - 列出所有别名\n"
    help_text += "  $$<command:show_alias_definitions>$$ 别名 - 显示指定别名的所有定义\n\n"
    
    # 管理员命令
    if is_admin:
        help_text += "管理员命令：\n"
        help_text += "  $$<command:del>$$ 问题 - 删除词条\n"
        help_text += "  $$<command:level>$$ - 显示当前用户的权限等级\n\n"
    
    # 超级管理员命令
    if is_super_admin:
        help_text += "超级管理员命令：\n"
        help_text += "  $$<command:admin>$$ QQ号 - 添加管理员\n"
        help_text += "  $$<command:level>$$ QQ号 等级 - 设置管理员等级（1-5）\n\n"
    
    # 系统命令
    help_text += "系统命令：\n"
    help_text += "  $$<command:status>$$ - 显示系统状态\n\n"
    
    help_text += "使用 '$$<command:help>$$ 命令名' 可以查看特定命令的详细说明。"
    
    return process_command_references(help_text)

def get_command_help(self, command, user_id):
    is_admin = self.word_manager.get_admin_level(user_id) > 0
    is_super_admin = self.word_manager.is_super_admin(user_id)

    help_dict = {
        "add": "添加新词条\n用法：#add 问题 答案\n说明：添加一个新的问答对到词条库中。答案可以包含文字和图片。",
        "query": "搜索词条\n用法：$$<command:query>$$ 关键词\n说明：搜索包含指定关键词的所有词条。",
        "requery": "使用正则表达式搜索词条\n用法：$$<command:requery>$$ 正则表达式\n说明：使用正则表达式搜索匹配的词条。",
        "show_all": "显示所有词条\n用法：#show_all\n说明：显示当前群组中的所有词条。",
        "show question": "显示问题\n用法：$$<command:show question>$$ <id/all> [每行显示数]\n说明：显示指定ID的问题或所有问题。当显示所有问题时，可以指定每行显示的问题数。",
        "show_answers": "显示问题的所有答案\n用法：$$<command:show_answers>$$ 问题\n说明：显示指定问题的所有答案。",
        "help": "显示帮助信息\n用法：$$<command:help>$$ [命令]\n说明：显示所有可用命令或特定命令的详细帮助。",
        "alias add": "添加命令别名\n用法：$$<command:alias add>$$ 别名 命令\n说明：为指定的命令添加一个别名。",
        "alias del": "删除命令别名\n用法：$$<command:alias del>$$ 别名\n说明：删除指定的命令别名。",
        "alias list": "列出所有别名\n用法：$$<command:alias list>$$\n说明：显示当前群组中所有已定义的别名。",
        "show_alias_definitions": "显示别名定义\n用法：$$<command:show_alias_definitions>$$ 别名\n说明：显示指定别名的所有定义。",
        "status": "显示系统状态\n用法：$$<command:status>$$\n说明：显示当前数据库词条数量、用户权限等级、数据库信息和图片目录大小。"
    }

    if is_admin:
        help_dict.update({
            "del": "删除词条（需要管理员权限）\n用法：$$<command:del>$$ 问题\n说明：删除指定问题的词条。",
            "level": "显示权限等级\n用法：$$<command:level>$$\n说明：显示当前用户的权限等级。"
        })

    if is_super_admin:
        help_dict.update({
            "admin": "添加管理员（需要超级管理员权限）\n用法：$$<command:admin>$$ QQ号\n说明：将指定QQ号添加为管理员。",
            "level": "显示或设置权限等级\n用法：$$<command:level>$$ [QQ号 等级]\n说明：不带参数时显示当前用户的权限等级，带参数时设置指定用户的权限等级（需要超级管理员权限）。"
        })

    if command not in help_dict:
        return f"未找到命令 '{command}' 的帮助信息。请使用 '$$<command:help>$$' 查看所有可用命令。"

    if (command in ["del"] and not is_admin) or (command in ["admin"] and not is_super_admin):
        return f"您没有使用 '{command}' 命令的权限。"

    return process_command_references(help_dict[command])
    return process_command_references(help_dict[command])

