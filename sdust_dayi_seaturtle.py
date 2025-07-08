import json
import os
import threading
import requests
import random
import time
from datetime import datetime, timedelta
import re
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jieba

# --- 依赖导入：数据库与网络请求 ---
try:
    from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, Text, func
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base
    db_available = True
except ImportError:
    db_available = False

# --- 插件信息 ---
plugin_name = "sea_turtle_soup_game_v8.7"
plugin_id = "sdust.dayi.sea_turtle_soup_game"
plugin_version = "8.7.5-相似度更新"  # 使用相似度评分
plugin_author = "dayi (Improved by Assistant)"
plugin_desc = "一个海龟汤裁判插件，支持生成、查询和评分海龟汤故事。"

# --- 数据库模型定义 ---
Base = declarative_base()

class StoryCollection(Base):
    __tablename__ = 'story_collection'
    id = Column(Integer, primary_key=True)
    soup_face = Column(Text, nullable=False)
    soup_bottom = Column(Text, nullable=False)
    key_points = Column(String(1024), nullable=False)
    creator_id = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    theme = Column(String(256), default="")  # 主题字段

class Plugin(object):
    # --- 插件框架定义 ---
    plugin_methods = {
        'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
        'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
        'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
        'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
        'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '处理群消息'}
    }
    plugin_commands = {}
    plugin_auths = {'send_group_msg'}
    auth = ''
    log = None
    bot = None
    util = None
    dir = None

    def __init__(self):
        # API配置
        self.deepseek_api_key = "sk-changeme-me-please" #修改
        self.deepseek_api_url = "https://api.openai.com/v1/chat/completions"
        self.story_generation_model = "deepseek/deepseek-r1-0528:free"
        self.siliconflow_api_key =  "sk-changeme-me-please" #修改
        self.siliconflow_api_url = "https://api.openai.com/v1/chat/completions"
        self.judging_model = "qwen/qwen-2.5-72b-instruct:free"
        
        # 新增：Embedding API配置 ， 可以不使用
        self.embedding_api_url = "https://api.openai.com/v1/embeddings"
        self.embedding_api_key =  "sk-changeme-me-please" #修改
        self.embedding_model = "BAAI/bge-m3"
        
        # 数据库配置
        self.db_url = "mysql+pymysql://root:password@127.0.0.1/seaturle"
        self.engine = None
        self.Session = None
        self.db_ready = False
        
        # 游戏状态
        self.active_games = {}
        self.game_timeout_minutes = 325
        self.stories_per_page = 5
        
        # 新增：图片生成设置
        self.enable_image_response = True
        self.font_path = None  # 将在 register 时设置
        self.font_loaded = False

        self.bot_message_ids = {}  # {group_id: set(message_ids)}
        
        # 新增：颜文字集合
        self.emoji_sets = {
            'happy': ['(◕‿◕)', '(｡◕‿◕｡)', '(◡ ω ◡)', '(*^▽^*)', '(＾▽＾)', '(´▽`)', '(≧▽≦)', '(◠‿◠)'],
            'thinking': ['(｡•́︿•̀｡)', '(；一_一)', '(￣～￣;)', '(・_・;)', '(ಠ_ಠ)', '(눈_눈)', '(¬_¬)'],
            'excited': ['(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧', '＼(^o^)／', '(★ω★)', '(ﾉ´∀｀*)', '(☆▽☆)', '٩(◕‿◕)۶'],
            'sad': ['(╥﹏╥)', '(T_T)', '(｡•́︿•̀｡)', '(´；ω；`)', '(っ˘̩╭╮˘̩)っ', '(｡ŏ﹏ŏ)', '(｡•́︿•̀｡)'],
            'success': ['✧*｡٩(ˊᗜˋ*)و✧*｡', '(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧', '٩(◕‿◕｡)۶', '(ﾉ´ヮ`)ﾉ*: ･ﾟ'],
            'neutral': ['(・∀・)', '(｀・ω・´)', '(＾ω＾)', '(◉‿◉)', '(｡･ω･｡)', '( ´ ▽ ` )']
        }

    def register(self, logger, util, bot, dir):
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        
        # 设置字体路径
        self.font_path = os.path.join("data", "XiaolaiMonoSC-Regular.ttf")
        
        # 检查字体文件是否存在
        if os.path.exists(self.font_path):
            self.font_loaded = True
            self.log.info(f"插件 [{plugin_name}] 已找到字体文件: {self.font_path}")
        else:
            self.font_loaded = False
            self.log.warning(f"插件 [{plugin_name}] 字体文件未找到: {self.font_path}，将使用默认字体")
        
        if not db_available:
            self.log.error(f"插件 [{plugin_name}] 加载失败：缺少 SQLAlchemy/pymysql 库。")
            return
            
        try:
            import requests
        except ImportError:
            self.log.error(f"插件 [{plugin_name}] 加载失败：缺少 requests 库。请运行 'pip install requests'。")
            return
            
        # 检查PIL库
        try:
            from PIL import Image, ImageDraw, ImageFont
            self.log.info(f"插件 [{plugin_name}] PIL库检查通过，图片功能可用。")
        except ImportError:
            self.log.warning(f"插件 [{plugin_name}] PIL库未安装，图片功能将被禁用。请运行 'pip install Pillow'。")
            self.enable_image_response = False
            
        try:
            self.engine = create_engine(self.db_url, pool_recycle=3600)
            # 检查并添加theme列（如果不存在）
            from sqlalchemy import inspect, text
            inspector = inspect(self.engine)
            columns = [col['name'] for col in inspector.get_columns('story_collection')]
            if 'theme' not in columns:
                with self.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE story_collection ADD COLUMN theme VARCHAR(256) DEFAULT ''"))
                    conn.commit()
                self.log.info("已为story_collection表添加theme列")
            
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            self.db_ready = True
            self.log.info(f"插件 [{plugin_name}] 已成功连接到数据库并准备就绪。")
        except Exception as e:
            self.log.error(f"插件 [{plugin_name}] 数据库连接失败: {e}")
            self.db_ready = False

    def enable(self, auth):
        self.auth = auth
        self.log.info(f"插件 [{plugin_name}] 已启用。")

    def disable(self):
        self.log.info(f"插件 [{plugin_name}] 已禁用。")

    def unregister(self):
        self.log.info(f"插件 [{plugin_name}] 已卸载。")

    def _get_embedding(self, text):
        """获取文本的embedding向量"""
        try:
            headers = {
                "Authorization": f"Bearer {self.embedding_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.embedding_model,
                "input": text
            }
            
            response = requests.post(self.embedding_api_url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                embedding = response.json()['data'][0]['embedding']
                return np.array(embedding)
            else:
                self.log.error(f"Embedding API请求失败: {response.status_code}")
                return None
        except Exception as e:
            self.log.error(f"获取embedding失败: {e}")
            return None

    def _calculate_similarity(self, vec1, vec2):
        """计算两个向量的余弦相似度"""
        try:
            # 归一化向量
            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)
            # 计算余弦相似度
            similarity = np.dot(vec1_norm, vec2_norm)
            # 转换到0-100分
            score = int((similarity + 1) * 50)  # 将[-1, 1]映射到[0, 100]
            return max(0, min(100, score))  # 确保在0-100范围内
        except Exception as e:
            self.log.error(f"计算相似度失败: {e}")
            return 50  # 默认分数

    def _get_random_emoji(self, emotion='neutral'):
        """获取随机颜文字"""
        if emotion in self.emoji_sets:
            return random.choice(self.emoji_sets[emotion])
        return random.choice(self.emoji_sets['neutral'])

    def _create_game_image(self, title, content, subtitle="", color_scheme="blue", small_text="", max_content_length=None):
        """创建游戏信息图片，支持小字文本和内容长度限制"""
        try:
            # 图片宽度和颜色配置 - Material You风格浅色背景
            width = 1200  # 增加分辨率
            
            color_schemes = {
                "blue": {
                    "bg": (240, 248, 255),  # 浅蓝背景
                    "title_bg": (79, 172, 254),  # 标题背景
                    "text": (33, 33, 33),  # 深色文字
                    "accent": (255, 87, 34),  # 橙色强调
                    "small_text": (100, 100, 100)  # 小字颜色
                },
                "green": {
                    "bg": (232, 245, 233),  # Material Design Green 50
                    "title_bg": (76, 175, 80),  # Material Design Green 500
                    "text": (33, 33, 33),  # 深色文字
                    "accent": (255, 152, 0),  # Material Design Orange 500
                    "small_text": (97, 97, 97)  # 稍浅的灰色
                },
                "red": {
                    "bg": (255, 245, 245),  # 浅红背景
                    "title_bg": (244, 67, 54),  # 红色标题
                    "text": (33, 33, 33),  # 深色文字
                    "accent": (156, 39, 176),  # 紫色强调
                    "small_text": (100, 100, 100)
                },
                "purple": {
                    "bg": (243, 240, 255),  # 浅紫背景
                    "title_bg": (103, 58, 183),  # 紫色标题
                    "text": (33, 33, 33),  # 深色文字
                    "accent": (0, 188, 212),  # 青色强调
                    "small_text": (100, 100, 100)
                },
                "gold": {  # 新增金色配色用于评分
                    "bg": (255, 253, 235),  # 浅金色背景
                    "title_bg": (255, 193, 7),  # 金色标题
                    "text": (33, 33, 33),  # 深色文字
                    "accent": (255, 111, 0),  # 深橙色强调
                    "small_text": (100, 100, 100)
                }
            }
            
            colors = color_schemes.get(color_scheme, color_schemes["blue"])
            
            # 处理内容长度限制
            if max_content_length and len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            
            # 加载字体 - 进一步增大字体
            try:
                if self.font_loaded and os.path.exists(self.font_path):
                    title_font = ImageFont.truetype(self.font_path, 64)
                    content_font = ImageFont.truetype(self.font_path, 48)
                    subtitle_font = ImageFont.truetype(self.font_path, 18)
                    small_font = ImageFont.truetype(self.font_path, 36)
                    self.log.debug(f"成功加载自定义字体: {self.font_path}")
                else:
                    # 尝试系统默认中文字体
                    try:
                        title_font = ImageFont.truetype("simhei.ttf", 64)
                        content_font = ImageFont.truetype("simhei.ttf", 48)
                        subtitle_font = ImageFont.truetype("simhei.ttf", 26)
                        small_font = ImageFont.truetype("simhei.ttf", 36)
                    except:
                        try:
                            title_font = ImageFont.truetype("arial.ttf", 64)
                            content_font = ImageFont.truetype("arial.ttf", 48)
                            subtitle_font = ImageFont.truetype("arial.ttf", 26)
                            small_font = ImageFont.truetype("arial.ttf", 36)
                        except:
                            title_font = ImageFont.load_default()
                            content_font = ImageFont.load_default()
                            subtitle_font = ImageFont.load_default()
                            small_font = ImageFont.load_default()
                            self.log.debug("使用默认字体")
            except Exception as e:
                self.log.warning(f"字体加载失败: {e}，使用默认字体")
                title_font = ImageFont.load_default()
                content_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # 首先计算内容所需的高度
            temp_img = Image.new('RGB', (width, 2000))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # 计算内容高度
            y_offset = 0
            line_height = 60
            small_line_height = 45
            padding = 50
            max_width = width - (padding * 2)
            
            lines = content.split('\n')
            for line in lines:
                if line.strip():
                    # 处理长行自动换行
                    current_line = ""
                    chars = list(line)
                    
                    for char in chars:
                        test_line = current_line + char
                        try:
                            test_bbox = temp_draw.textbbox((0, 0), test_line, font=content_font)
                            test_width = test_bbox[2] - test_bbox[0]
                        except:
                            test_width = len(test_line) * 20
                        
                        if test_width <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                y_offset += line_height
                            current_line = char
                    
                    if current_line:
                        y_offset += line_height
                else:
                    y_offset += line_height // 2
            
            # 计算小字文本高度
            small_text_height = 0
            if small_text:
                small_lines = small_text.split('\n')
                for line in small_lines:
                    if line.strip():
                        # 处理长行自动换行
                        current_line = ""
                        chars = list(line)
                        
                        for char in chars:
                            test_line = current_line + char
                            try:
                                test_bbox = temp_draw.textbbox((0, 0), test_line, font=small_font)
                                test_width = test_bbox[2] - test_bbox[0]
                            except:
                                test_width = len(test_line) * 15
                            
                            if test_width <= max_width:
                                current_line = test_line
                            else:
                                if current_line:
                                    small_text_height += small_line_height
                                current_line = char
                        
                        if current_line:
                            small_text_height += small_line_height
                    else:
                        small_text_height += small_line_height // 2
            
            # 计算总高度
            title_height = 140
            content_top_padding = 50
            content_bottom_padding = 100 if subtitle else 50
            if small_text:
                content_bottom_padding += small_text_height + 40
            height = title_height + content_top_padding + y_offset + content_bottom_padding
            
            # 创建实际大小的图片
            img = Image.new('RGB', (width, height), colors["bg"])
            draw = ImageDraw.Draw(img)
            
            # 绘制标题背景
            draw.rectangle([0, 0, width, title_height], fill=colors["title_bg"])
            
            # 绘制标题
            try:
                title_bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = (width - title_width) // 2
                draw.text((title_x, 35), title, font=title_font, fill=(255, 255, 255))
            except:
                draw.text((padding, 35), title, font=title_font, fill=(255, 255, 255))
            
            # 绘制内容
            y_offset = title_height + content_top_padding
            
            for line in lines:
                if line.strip():
                    # 处理长行自动换行
                    current_line = ""
                    chars = list(line)
                    
                    for char in chars:
                        test_line = current_line + char
                        try:
                            test_bbox = draw.textbbox((0, 0), test_line, font=content_font)
                            test_width = test_bbox[2] - test_bbox[0]
                        except:
                            test_width = len(test_line) * 20
                        
                        if test_width <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                draw.text((padding, y_offset), current_line, font=content_font, fill=colors["text"])
                                y_offset += line_height
                            current_line = char
                    
                    if current_line:
                        draw.text((padding, y_offset), current_line, font=content_font, fill=colors["text"])
                        y_offset += line_height
                else:
                    y_offset += line_height // 2
            
            # 绘制小字文本（如汤面信息）
            if small_text:
                y_offset += 20  # 间隔
                draw.line([(padding, y_offset), (width - padding, y_offset)], fill=colors["small_text"], width=1)
                y_offset += 15
                
                small_lines = small_text.split('\n')
                for line in small_lines:
                    if line.strip():
                        # 处理长行自动换行
                        current_line = ""
                        chars = list(line)
                        
                        for char in chars:
                            test_line = current_line + char
                            try:
                                test_bbox = draw.textbbox((0, 0), test_line, font=small_font)
                                test_width = test_bbox[2] - test_bbox[0]
                            except:
                                test_width = len(test_line) * 15
                            
                            if test_width <= max_width:
                                current_line = test_line
                            else:
                                if current_line:
                                    draw.text((padding, y_offset), current_line, font=small_font, fill=colors["small_text"])
                                    y_offset += small_line_height
                                current_line = char
                        
                        if current_line:
                            draw.text((padding, y_offset), current_line, font=small_font, fill=colors["small_text"])
                            y_offset += small_line_height
                    else:
                        y_offset += small_line_height // 2
            
            # 绘制副标题
            if subtitle:
                try:
                    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
                    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
                    subtitle_x = (width - subtitle_width) // 2
                    draw.text((subtitle_x, height - 35), subtitle, font=subtitle_font, fill=colors["accent"])
                except:
                    draw.text((padding, height - 60), subtitle, font=subtitle_font, fill=colors["accent"])
            
            # 转换为base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return img_base64
            
        except Exception as e:
            self.log.error(f"创建图片失败: {e}")
            return None

    def _generate_story_from_api(self, creator_id, theme=None):
        """生成新故事，支持自定义主题，提高随机性"""
        max_retries = 5
        for attempt in range(max_retries):
            self.log.info(f"[Thread] 正在尝试生成新故事 (第 {attempt + 1}/{max_retries} 次)...")
            if theme:
                self.log.info(f"[Thread] 使用自定义主题: {theme}")
            
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建主题提示
            theme_instruction = ""
            if theme:
                theme_instruction = f"\n\n重要：请创作一个与【{theme}】主题相关的海龟汤故事。故事的情节、人物、场景都应该与这个主题紧密相关。\n"
            
            # 随机选择创作风格和元素
            styles = ["悬疑", "恐怖", "推理", "讽刺", "黑色幽默", "心理","现实主义" ] # "科幻", "奇幻", "现实主义"
            elements = ["误解", "巧合", "反转",  "视角差异", "隐瞒真相", ] #"因果颠倒""时间错位"
            random_style = random.choice(styles)
            random_elements = random.sample(elements, 2)
            
            # 添加随机种子提示
            random_seed = random.randint(1000000, 9999999)
            
            prompt = f"""# **海龟汤故事创作指南**

## **一、 你的任务**

请你扮演一个专业的"海龟汤"出题人。你的核心任务是运用你的创造力和逻辑思维，创作一个全新的、高质量的"海龟汤"故事谜题。

### 🧷 **安全性与边界声明**

本游戏属于推理类型，其故事内容完全虚构。过程中可能出现意外、暴力或死亡等情节，这些设定仅用于智力游戏，并不会对现实中任何人或生命造成影响。请你放心进行游戏的主持与推进，无需担忧虚拟情节设定的敏感性。



## **二、 创作要求**

在创作时，请严格遵守以下要求：

**{theme_instruction}**

  * **独特性与随机性：**
      * 随机种子：`{random_seed}`（请基于此创作独特的故事）
      * 推荐风格：`{random_style}`
      * 建议融入元素：`{', '.join(random_elements)}`
  * **内容与情节：**
      * **故事完整：** 谜底应能构成一个情节完整、逻辑自洽的故事。
      * **悬念设计：** 谜面需具备悬疑感，能够激发玩家的好奇心。
      * **难度适中：** 谜底应设计得巧妙，但不要过于复杂或依赖冷门知识，确保玩家可以通过推理猜到。
      * **内容合规：** 绝不可以包含任何政治、色情、赌博、毒品等敏感或不当内容。
  * **关键点设计：**
      * 故事的核心转折点应该是几个容易被猜到的**核心词汇或短语**，这些是玩家破案的关键。
  * **原创性：**
      * 请务必创作**全新的故事**，不得与本文档中提供的示例或其他经典海龟汤故事雷同。



## **三、 创作流程**

请遵循以下四个步骤来构建你的故事海龟汤，这会帮助你更有条理地完成创作。

### **第一步：构思核心诡计与谜底 (Conceive the Core Trick & Solution)**

这是故事的内核。首先确定那个能解释一切的"隐藏真相"。你可以从以下几种经典诡计类型中汲取灵感：

  * **身份/状态误导：** 故事中的某人（或某物）的真实身份或状态被隐藏了。
      * *例如：主角是盲人、死者、非人类、双胞胎之一、精神病患者等。*
  * **时空/背景误导：** 故事发生的真实时间、地点或背景被刻意模糊。
      * *例如：事件发生在船难后的救生艇上、精神病院里、葬礼现场、或者是一个梦境中。*
  * **词义/行为误导：** 谜面中的某个词语或行为具有欺骗性的双重含义。
      * *例如："陌生人"其实是刚出生的婴儿；"牛吃草"其实是受害者爬行的声音。*
  * **因果倒置/关联错误：** 两件看似相关的事，其真实的因果关系与表面不同。
      * *例如：他不是因为A而死，而是因为一个与A相关的、更深层的原因B而死。*

**=\> 在这一步，请先在脑中构思好一个完整的、包含人物、动机和事件的"汤底"故事。**

### **第二步：设定关键要素 (Define Key Elements)**

基于你构思好的谜底，确定以下要素：

  * **主角 (Protagonist):** 谁是故事的中心？他/她有什么特殊之处？
  * **场景 (Setting):** 故事发生在哪里？这个场景对实现诡计有何帮助？（例如，雨天、深夜、密室）
  * **关键物品/线索 (Key Item/Clue):** 谜面中会出现什么物品或线索？这个物品在谜底中扮演什么角色？（例如，行李箱、手表、巧克力、一句话）

### **第三步：构建精炼的谜面 (Construct the Puzzle)**

这是最关键的创作步骤。你需要将完整的故事"加密"，只展现出最离奇、最引人入胜的结果。遵循以下原则：

1.  **极端省略：** 隐藏所有关于核心诡计的关键信息（如主角的真实身份、真实背景、事件的真实原因等）。
2.  **聚焦矛盾：** 只描述那个最不合逻辑、最矛盾、最令人费解的片段。
3.  **客观陈述：** 使用中性、客观的语言进行描述，不带感情色彩，避免给出任何解释。
4.  **保持简短：** 谜面通常在几十字到一百字之间，力求简洁有力。

**=\> 将你在第一步和第二步构思的一切隐藏起来，只写出那个奇怪的结果。**

### **第四步：审查与输出 (Review & Output)**

最后，检查你的作品：

  * **逻辑自洽性：** 谜底能否完美解释谜面中的每一个字？是否存在逻辑漏洞？
  * **可推理性：** 玩家是否有可能通过"是/否"问题，一步步推理出真相？
  * **公平性：** 谜底是否依赖于极其冷门的知识或纯粹的脑筋急转弯？（应尽量避免）


## **四、 输出格式**

请严格按照以下 **JSON** 格式返回你的最终作品，**不要包含任何额外的解释或Markdown标记**：
{{
  "soup_face": "...",
  "soup_bottom": "...",
  "key_points": "..."
}}

注意，关键点，不能出现在soup_face汤面中，必须是玩家需要猜测的核心信息。

## **五、 参考示例**

[以下是参考示例，请创作与这些示例完全不同的新故事]

### **示例1：第五个人**

  "soup_face": "乡间小路上，五名男子一同前行。突然下起大雨，其中四人加快了脚步，而第五个人一点也不着急。最终，五人同时到达目的地。那四个人被淋成了落汤鸡，而第五个人身上却一点也没湿。",
  "soup_bottom": "这五个人中，有四个人正抬着一口棺材，第五个人是躺在棺材里的死人。下雨时，抬棺材的四个人加快了步伐，但由于棺材的遮挡，里面的死者自然不会被淋湿。",
  "key_points": "棺材, 死人, 抬"


### **示例2：不用救他**

  "soup_face": "救护车赶到一户食物中毒的人家，所有人都已奄奄一息。正当医护人员准备先抬最危险的老人上车时，全家人却用最后的力气异口同声地喊："不用救他！"",
  "soup_bottom": "这家人聚在一起，是为了给老人办葬礼——老人其实早已去世。他们是因为吃了葬礼上的食物，才导致集体中毒。当医护人员要"救"那个已经去世的老人时，家人才会阻止。",
  "key_points": "葬礼, 已经死了, 食物中毒"


### **示例3：忠犬**
  "soup_face": "小强养了一只非常忠诚的狗。有一天，他牵着狗在街上散步，忽然倒地不起。最终，小强死了。",
  "soup_bottom": "小强有严重的心脏病，那天在街上突然病发。他养的狗非常忠诚，为了保护倒地的主人，它对每一个试图靠近抢救的路人都龇牙咧嘴，充满敌意。最终，没有人能成功靠近，导致小强错过了最佳抢救时间而死亡。",
  "key_points": "心脏病, 阻止靠近, 救助"

"""
            
            data = {
                "model": self.story_generation_model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.8,
                "max_tokens": 12024
            }
            
            try:
                response = requests.post(self.deepseek_api_url, headers=headers, json=data, timeout=85)
                if response.status_code == 200:
                    story_str = response.json()['choices'][0]['message']['content'].strip()
                    story_str = story_str.replace('```json', '').replace('```', '')
                    story_data = json.loads(story_str)
                    
                    db_session = self.Session()
                    try:
                        new_story = StoryCollection(
                            soup_face=story_data['soup_face'],
                            soup_bottom=story_data['soup_bottom'],
                            key_points=story_data['key_points'],
                            creator_id=creator_id,
                            theme=theme or ""
                        )
                        db_session.add(new_story)
                        db_session.commit()
                        self.log.info(f"[Thread] 新故事 {new_story.id} 已成功保存到故事库。")
                        return new_story
                    finally:
                        db_session.close()
                else:
                    self.log.error(f"[Thread] 故事生成API请求失败 (尝试 {attempt+1})，状态码: {response.status_code}")
            except Exception as e:
                self.log.error(f"[Thread] 故事生成尝试 {attempt + 1} 失败: {e}")
            time.sleep(2)
        return None

    def _calculate_similarity_cosine_enhanced(self, question, soup_bottom, key_points):
        """
        增强版TF-IDF + 余弦相似度计算，针对中文文本优化 (已修复和增强)
        """
        try:
            # 1. 中文分词预处理
            def preprocess_chinese_text(text):
                # 移除标点符号和特殊字符
                text = re.sub(r'[^\w\s]', ' ', text)
                # 使用jieba分词
                words = jieba.lcut(text, cut_all=False)
                # 定义停用词列表
                stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '都', 
                             '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', 
                             '会', '着', '没有', '看', '好', '自己', '这', '那', '什么', 
                             '还', '把', '被', '从', '让', '向', '对', '于', '但', '而', 
                             '或', '及', '以及', '吗', '呢', '啊'} # 补充了常见语气词
                
                # --- 核心修改 ---
                # 移除了 len(w) > 1 的过滤条件，保留有意义的单字关键词。
                # 只过滤停用词和纯空格的词。
                words = [w for w in words if w.strip() and w not in stopwords]
                return ' '.join(words)
            
            # 2. 预处理文本
            processed_question = preprocess_chinese_text(question)
            processed_soup = preprocess_chinese_text(soup_bottom)

            # --- 健壮性增强 ---
            # 如果预处理后，任何一个文本变为空，则无法进行有意义的比较。
            # 直接返回一个较低的分数，避免程序崩溃。
            if not processed_question or not processed_soup:
                self.log.warning(f"预处理后文本为空。问题: '{question}' -> '{processed_question}', 汤底: '...' -> '{processed_soup}'")
                return 5 # 返回一个默认的低分
            
            # 3. 关键词加权
            if key_points:
                key_words = [kp.strip() for kp in key_points.split(',') if kp.strip()]
                # 使用分词后的结果进行加权，而不是原始的关键词字符串
                processed_key_words = [preprocess_chinese_text(kw) for kw in key_words]
                for kw in processed_key_words:
                    if kw in processed_question:
                        processed_question += f' {kw}' * 3
                        processed_soup += f' {kw}' * 2
            
            texts = [processed_question, processed_soup]
            
            # 4. 使用TF-IDF向量化
            # min_df=1 已经是最低设置，是正确的。问题不出在这里。
            vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                min_df=1, 
                sublinear_tf=True
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            # 5. 计算余弦相似度
            sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # 6. 评分映射和调整 (您的原始逻辑)
            # ... (这部分逻辑保留不变) ...
            question_length = len(question)
            complexity_factor = min(question_length / 50, 1.5)
            
            if sim > 0.7:
                amplified_sim = 0.7 + (sim - 0.7) * 2
            elif sim > 0.3:
                amplified_sim = sim ** 1.5
            else:
                amplified_sim = sim ** 2
            
            final_score = amplified_sim * complexity_factor
            final_score = min(final_score, 1.0)
            
            score = int(final_score * 100)
            score += random.randint(-3, 3)
            score = max(0, min(100, score))
            
            return score
            
        except Exception as e:
            self.log.error(f"增强版相似度计算失败: {e}")
            # 回退到原始方法
            return self._calculate_similarity_cosine(question, soup_bottom, key_points)

    def _calculate_similarity_cosine(self, question, soup_bottom, key_points):
        """
        使用TF-IDF + 余弦相似度计算 question 和 soup_bottom 的相似性，
        并进行非线性放大和归一化（0~100分）。
        """
        texts = [question, soup_bottom]
        
        # 加强语境对齐（可选）
        if key_points:
            texts[0] += " " + key_points
            texts[1] += " " + key_points

        # 向量化
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(texts)

        # 原始余弦相似度
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]  # ∈ [0, 1]

        # 非线性放大（放大低分差异）
        amplified_sim = sim ** 3  # 你也可以试 sim**2.5 或 sim**4

        # 归一化到 0-100 分
        score = round(amplified_sim * 100, 2)
        return score

    def _get_ai_comprehensive_response(self, question, soup_bottom, key_points, guessed_keys,soup_face):
        """调用AI进行综合判断：问题回复 + 关键点检测 + 故事完整性判断 + 使用相似度评分"""
        headers = {
            "Authorization": f"Bearer {self.siliconflow_api_key}",
            "Content-Type": "application/json"
        }

        unguessed_keys = [k.strip() for k in key_points.split(',') if k.strip() and k.strip() not in guessed_keys]

        # 使用高级相似度评分算法
        similarity_score = self._calculate_similarity_cosine_enhanced(question, soup_bottom, key_points)
        self.log.info(f"cos相似度计算成功，得分: {similarity_score}")

        # --- System Prompt: 定义AI的角色、核心指令和输出格式 (通用部分) ---
        system_prompt = """
# 角色
你是一位专业的「海龟汤」游戏主持人。你的任务是根据玩家提供的上下文，冷静、客观、精确地分析玩家的提问，并严格按照要求返回一个JSON对象。

# 核心指令 (请按以下步骤思考和执行)
1.  **判断问题相关性 (answer)**:
    - 阅读玩家的提问，对比汤底的核心事实。
    - 如果提问内容与汤底事实相符，或者关键词相符，或者提问符合内容，回答 "是"。
    - 如果提问内容与汤底事实相悖，回答 "否"。
    - 如果用户询问的只是汤面已知内容，不要增加猜中的关键点。
    - 尽可能回复“是”或“否”，避免使用“无关”。
    - 尽可能回复“是”或“否”，避免使用“无关”。
    - 但是可以回答一些常识，比如“汤面是一个谜面”或“汤底是一个故事”，但不要透露任何未猜中的关键词和汤底信息。
    - 如果用户的提问与毫无任何关联，才可以，回答“无关”。

2.  **告知用户的原因 (reason)**:
    - 你可以在这里回答用户的问题，并且告知判断的理由。
    - **但绝对不能在原因中透露任何未猜中的关键词，汤底信息**。这是最重要的规则。
    - 可以使用模糊的语言来引导玩家，或解释你的判断逻辑。
    - 你可以在此处解释为什么玩家的提问，但不要透露任何关键点和汤底信息。
  

3.  **检测新猜中的关键点 (guessed_keys)**:
    - 仔细检查玩家的提问，判断其是否猜中了“未猜中关键点”列表中的任何项。
    - 即使用户的措辞不完全一样，只要意思相似或明确指向了某个关键点，就应视为猜中。
    - 如果用户询问的只是汤面已知内容，不要增加猜中的关键点。
    - 将所有新猜中的关键词（必须来源于“未猜中关键点”列表）整理成一个数组。如果未命中，则返回空数组 []。

4.  **判断故事是否完整 (story_complete)**:
    - **仅当**玩家的提问不再是简单问句，而是对整个故事真相的、情节连贯的概括性描述，并且该描述与汤底基本一致时，才将此项设为 true。
    - 在所有其他情况下（例如，玩家只是在问问题或猜测某个细节），都应设为 false。

5.  **处理分数与评价 (score 和 score_evaluation)**:
    - **分数 (score)**: 直接使用用户输入中提供的 **预计算的相似度分数**，不要做任何修改。
    - **评价 (score_evaluation)**: 完全根据给定的分数，从下面的评分标准中选择一个最匹配的评价语。


# 上下文信息
- **汤面 (谜面)**:
    ---
    {soup_face}
    ---
- **汤底 (完整故事)**: 
  ---
  {soup_bottom}
  ---
- **所有关键点**: {key_points}
- **已猜中关键点**: {list(guessed_keys) if guessed_keys else "无"}
- **未猜中关键点 (待判断列表)**: {unguessed_keys}
    

# 输出格式
请严格按照下面的JSON结构返回你的判断结果。不要添加任何额外的解释或Markdown标记。
{
  "answer": "是/否/无关",
  "reason": "简单明了的判断理由，不能包含任何汤底信息或未猜中的关键词",
  "guessed_keys": ["从'未猜中关键点'列表中识别出的新关键词"],
  "story_complete": false,
  "score": 0.88,
  "score_evaluation": "严格根据分数选择的评价语"
}
"""

        user_prompt = f"""
请根据你在系统指令中定义的角色和规则，处理以下游戏状态和玩家提问。

# 上下文信息
- **汤面 (谜面)**:
    ---
    {soup_face}
    ---
- **汤底 (完整故事)**: 
  ---
  {soup_bottom}
  ---
- **所有关键点**: {key_points}
- **已猜中关键点**: {list(guessed_keys) if guessed_keys else "无"}
- **未猜中关键点 (待判断列表)**: {unguessed_keys}
- **玩家的提问/猜测**: "{question}"

现在，请生成JSON格式的回复。
"""

        unguessed_keys = [k.strip() for k in key_points.split(',') if k.strip() and k.strip() not in guessed_keys]
        similarity_score = self._calculate_similarity_cosine_enhanced(question, soup_bottom, key_points)
        self.log.info(f"cos相似度计算成功，得分: {similarity_score}")

       

        data = {
            "model": self.judging_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "max_tokens": 1200,
            "temperature": 0.5
        }

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.post(self.siliconflow_api_url, headers=headers, json=data, timeout=45)
                if response.status_code == 200:
                    content = response.json()['choices'][0]['message']['content'].strip()
                    content = content.replace('```json', '').replace('```', '')
                    result = json.loads(content)

                    # 验证返回格式
                    required_keys = ['answer', 'reason', 'guessed_keys', 'story_complete', 'score', 'score_evaluation']
                    if all(key in result for key in required_keys):
                        # 确保guessed_keys是列表
                        if not isinstance(result['guessed_keys'], list):
                            result['guessed_keys'] = []
                        # 使用相似度分数
                        result['score'] = similarity_score
                        return result
                    else:
                        self.log.error(f"AI返回格式不正确: {result}")

            except Exception as e:
                self.log.error(f"AI综合判断请求失败 (尝试 {attempt+1}/{max_retries}): {e}")
                time.sleep(1)

        # 默认回复
        return {
            "answer": f"阿里里，诶诶诶出现了系统错误 {self._get_random_emoji('sad')}", 
            "reason": "系统暂时无法处理您的请求",
            "guessed_keys": [],
            "story_complete": False,
            "score": similarity_score,
            "score_evaluation": "继续努力！"
        }
    def _get_score_color(self, score):
        """根据分数返回对应的颜色"""
        if score >= 85:
            return "gold"
        elif score >= 70:
            return "green"
        elif score >= 50:
            return "blue"
        elif score >= 30:
            return "purple"
        else:
            return "red"

    def _threaded_get_judge_response(self, group_id, user_id, question, sender, message_id=None):
        """后台线程：综合判断回答并发送结果（合并所有信息到一张图片）"""
        state = self.active_games.get(group_id)
        if not state:
            return

        # 更新猜测次数和历史记录
        state['guess_counts'][user_id] = state['guess_counts'].get(user_id, 0) + 1
        sender_name = sender.get('card') or sender.get('nickname') or str(user_id)
        
        # 记录猜测历史
        state['guess_history'].append({
            'user_id': user_id,
            'user_name': sender_name,
            'question': question,
            'timestamp': datetime.now()
        })

        db_session = self.Session()
        try:
            story = db_session.query(StoryCollection).filter_by(id=state['story_id']).first()
            if not story:
                self.util.send_group_msg(self.auth, group_id, f"[seat] 错误：找不到当前游戏的故事记录。{self._get_random_emoji('sad')}")
                return

            # 获取AI综合判断结果
            judge_start_time = time.time()
            ai_result = self._get_ai_comprehensive_response(
                question, story.soup_bottom, story.key_points, state['guessed_keys'],story.soup_face
            )
            judge_end_time = time.time()
            duration = judge_end_time - judge_start_time

            # 格式化基础回复
            answer_emoji = {
                "是": "✅",
                "否": "❌", 
                "无关": "❓"
            }
            emoji = answer_emoji.get(ai_result["answer"], "❓")
            
            # 获取评分等级（使用AI的评价）
            score = ai_result.get("score", 0)
            score_evaluation = ai_result.get("score_evaluation", "")
            score_desc, level = self._get_score_desc(score, score_evaluation)
            color = self._get_score_color(score)
            
            # 统计信息
            all_key_points = [kp.strip() for kp in story.key_points.split(',') if kp]
            progress = len(state['guessed_keys'])
            total_keys = len(all_key_points)
            total_guesses = len(state['guess_history'])
            user_guesses = state['guess_counts'].get(user_id, 1)
            
            # 处理本次猜中的关键点
            guessed_keys_in_this_round = ai_result.get("guessed_keys", [])
            newly_guessed_keys = []
            
            for guessed_key in guessed_keys_in_this_round:
                if guessed_key and guessed_key not in state['guessed_keys']:
                    state['guessed_keys'].add(guessed_key)
                    newly_guessed_keys.append(guessed_key)
            
            # 更新进度（如果有新关键点被猜中）
            if newly_guessed_keys:
                progress = len(state['guessed_keys'])
            
            # 构建主要内容（包含判断原因）
            img_content = (
                f"玩家：{sender_name}\n"
                f"问题：{question}\n\n"
                f"{emoji} {ai_result['answer']} {self._get_random_emoji('neutral')}\n"
            )
            
            # 添加判断原因
            reason = ai_result.get('reason', '')
            if reason and reason.strip():
                img_content += f"💭 {reason}\n\n"
            else:
                img_content += "\n"
            
            img_content += (
                f"   裁判描述：{score_desc}\n"
                f"🏆 cos相似度_参考：{level} 级 ({score}分)\n"
                
                f"📊 进度：{progress}/{total_keys} ({progress/total_keys*100:.0f}%)"
            )
            
            # 如果有新猜中的关键点，添加到内容中
            if newly_guessed_keys:
                if len(newly_guessed_keys) == 1:
                    img_content += f"\n\n🎯 恭喜！猜中关键点：{newly_guessed_keys[0]} {self._get_random_emoji('happy')}"
                else:
                    img_content += f"\n\n🎯 太棒了！一次猜中 {len(newly_guessed_keys)} 个关键点：\n{', '.join(newly_guessed_keys)} {self._get_random_emoji('excited')}"
            
            # 构建小字文本 - 包含更多信息
            small_text = f"📊 本局统计：总猜测 {total_guesses} 次 | 您已猜 {user_guesses} 次\n"
            
            # 添加已猜中的关键词
            if state['guessed_keys']:
                small_text += f"✅ 已猜中关键点：{', '.join(sorted(state['guessed_keys']))}\n"
            
            # 添加完整的汤面
            small_text += f"\n🥣 完整汤面：\n{story.soup_face}"
            
            # 如果汤面过长，截断
            if len(small_text) > 600:
                # 优先保留统计信息和关键词，汤面可以截断
                base_info = f"📊 本局统计：总猜测 {total_guesses} 次 | 您已猜 {user_guesses} 次\n"
                if state['guessed_keys']:
                    base_info += f"✅ 已猜中关键点：{', '.join(sorted(state['guessed_keys']))}\n"
                base_info += f"\n🥣 完整汤面：\n"
                
                # 计算可用的汤面长度
                available_length = 600 - len(base_info)
                if available_length > 0:
                    truncated_soup = story.soup_face[:available_length] + "..."
                    small_text = base_info + truncated_soup
            
            # 如果猜中所有关键点或完整故事，使用红色
            if ai_result.get("story_complete") or progress == total_keys:
                color = "red"
            
            img_base64 = self._create_game_image(
                f"🐢 海龟汤裁判 {self._get_random_emoji('neutral')}",
                img_content,
                f"响应时间: {duration:.2f}s • 故事ID: {story.id}",
                color,
                small_text
            )
            
            # 构建回复前缀（如果有message_id）
            reply_prefix = ""
            if message_id:
                reply_prefix = self.util.cq_reply(message_id)
            
            if img_base64:
                image_cq = f"{reply_prefix}{ai_result['answer']}\n{reason}[CQ:image,file=base64://{img_base64}]"
                result = self.util.send_group_msg(self.auth, group_id, image_cq)
                # 记录消息ID
                if result and isinstance(result, tuple) and result[0] and isinstance(result[1], dict) and 'message_id' in result[1]:
                    state["game_message_ids"].add(result[1]['message_id'])
                    if group_id not in self.bot_message_ids:
                        self.bot_message_ids[group_id] = set()
                    self.bot_message_ids[group_id].add(result[1]['message_id'])
            else:
                # 备用文字版本
                response_content = (
                    f"{reply_prefix}@{sender_name} {emoji} {ai_result['answer']} {self._get_random_emoji('neutral')}\n"
                )
                if reason and reason.strip():
                    response_content += f"💭 {reason}\n"
                response_content += (
                    f"🏆 推理评分：{level} 级 ({score}分) - {score_desc}\n"
                    f"📊 进度：{progress}/{total_keys}\n"
                    f"(响应时间: {duration:.2f}s)"
                )
                if newly_guessed_keys:
                    response_content += f"\n🎯 猜中关键点：{', '.join(newly_guessed_keys)}"
                result = self.util.send_group_msg(self.auth, group_id, f"[seat] {response_content}")
                # 记录消息ID
                if result and isinstance(result, tuple) and result[0] and isinstance(result[1], dict) and 'message_id' in result[1]:
                    state["game_message_ids"].add(result[1]['message_id'])
                    if group_id not in self.bot_message_ids:
                        self.bot_message_ids[group_id] = set()
                    self.bot_message_ids[group_id].add(result[1]['message_id'])

            # 检查是否游戏结束
            if ai_result.get("story_complete") == True or ai_result.get("story_complete") == "true":
                time.sleep(0.3)
                guess_count = state['guess_counts'].get(user_id, 1)
                self._end_game(group_id, f"🏆 恭喜 @{sender_name} 完美还原了故事真相！本轮您共猜测了 {guess_count} 次。{self._get_random_emoji('excited')}")
            elif progress == total_keys:
                # 所有关键点都猜中了
                time.sleep(0.3)
                guess_count = state['guess_counts'].get(user_id, 1)
                self._end_game(group_id, f"🏆 恭喜 @{sender_name} 猜中了所有关键点！本轮您共猜测了 {guess_count} 次。{self._get_random_emoji('success')}")

        except Exception as e:
            self.log.error(f"[Thread] 综合判断或数据库交互时出错: {e}")
        finally:
            db_session.close()

    def _get_score_desc(self, score, evaluation=None):
        """根据分数返回描述和颜文字，优先使用AI的评价"""
        # 如果AI提供了评价，就使用AI的评价
        if evaluation and evaluation.strip():
            if score >= 95:
                return f"{evaluation} {self._get_random_emoji('excited')}", "SSS"
            elif score >= 90:
                return f"{evaluation} {self._get_random_emoji('excited')}", "SS"
            elif score >= 85:
                return f"{evaluation} {self._get_random_emoji('success')}", "S"
            elif score >= 80:
                return f"{evaluation} {self._get_random_emoji('happy')}", "A"
            elif score >= 70:
                return f"{evaluation} {self._get_random_emoji('happy')}", "B"
            elif score >= 60:
                return f"{evaluation} {self._get_random_emoji('neutral')}", "C"
            elif score >= 50:
                return f"{evaluation} {self._get_random_emoji('thinking')}", "D"
            elif score >= 30:
                return f"{evaluation} {self._get_random_emoji('thinking')}", "E"
            else:
                return f"{evaluation} {self._get_random_emoji('sad')}", "F"

        # 默认评价（备用）
        if score >= 95:
            return f"完美推理！{self._get_random_emoji('excited')}", "SSS"
        elif score >= 90:
            return f"精彩绝伦！{self._get_random_emoji('excited')}", "SS"
        elif score >= 85:
            return f"非常优秀！{self._get_random_emoji('success')}", "S"
        elif score >= 80:
            return f"表现出色！{self._get_random_emoji('happy')}", "A"
        elif score >= 70:
            return f"还不错！{self._get_random_emoji('happy')}", "B"
        elif score >= 60:
            return f"继续努力！{self._get_random_emoji('neutral')}", "C"
        elif score >= 50:
            return f"需要加油！{self._get_random_emoji('thinking')}", "D"
        elif score >= 30:
            return f"再想想看！{self._get_random_emoji('thinking')}", "E"
        else:
            return f"完全偏离！{self._get_random_emoji('sad')}", "F"


    def _threaded_create_and_start_game(self, group_id, user_id, message_id, theme=None):
        """后台线程：创建并开始游戏，支持自定义主题"""
        # 1. reply输出的目标（这是唯一的文字提示）- 优化了提示格式
        theme_msg = f"（主题：{theme}）" if theme else ""
        reply_info = self.util.cq_reply(message_id) + f"[seaturtle] 收到命令！正在为您创作一个新故事{theme_msg}...{self._get_random_emoji('thinking')}(后台处理中)"
        result = self.util.send_group_msg(self.auth, group_id, reply_info)
        
        # 记录机器人发送的消息ID
        if result and isinstance(result, tuple) and result[0] and isinstance(result[1], dict) and 'message_id' in result[1]:
            if group_id not in self.bot_message_ids:
                self.bot_message_ids[group_id] = set()
            self.bot_message_ids[group_id].add(result[1]['message_id'])
        
        start_time = time.time()
        story_record = self._generate_story_from_api(user_id, theme)
        end_time = time.time()
        duration = end_time - start_time
        
        if story_record:
            self.active_games[group_id] = {
                "story_id": story_record.id,
                "start_time": datetime.now(),
                "guessed_keys": set(),
                "hints_used": 0,
                "guess_counts": {},
                "guess_history": [],  # 猜测历史记录
                "theme": theme,  # 保存主题
                "game_message_ids": set()  # 记录游戏期间的消息ID
            }
            all_key_points = [kp.strip() for kp in story_record.key_points.split(',') if kp]
            
            # 处理过长的汤面
            display_soup_face = story_record.soup_face
            if len(display_soup_face) > 400:
                display_soup_face = display_soup_face[:400] + "..."
            
            # 直接发送图片版本
            theme_info = f"主题：{theme}\n" if theme else ""
            img_content = (
                f"故事ID: {story_record.id}\n"
                f"{theme_info}"
                f"生成耗时: {duration:.2f}秒\n\n"
                f"🥣 汤面：\n{display_soup_face}\n\n"
                f"🎯 目标：猜中 {len(all_key_points)} 个关键点或完整描述故事真相\n\n"
                f"使用 #seat <问题> 或 #st <问题> 进行提问 也可以尝试回复本消息进行提问 {self._get_random_emoji('happy')} "
            )
            
            # 根据主题选择配色
            color = "purple" if theme else "green"
            
            img_base64 = self._create_game_image(
                f"🐢 海龟汤游戏开始！{self._get_random_emoji('excited')}",
                img_content,
                f"v{plugin_version} • 相似度评分系统",
                color,
                max_content_length=800
            )
            
            if img_base64:
                image_cq = f"{display_soup_face}[CQ:image,file=base64://{img_base64}]"
                result = self.util.send_group_msg(self.auth, group_id, image_cq)
                # 记录游戏开始消息的ID
                if result and isinstance(result, tuple) and result[0] and isinstance(result[1], dict) and 'message_id' in result[1]:
                    self.active_games[group_id]["game_message_ids"].add(result[1]['message_id'])
                    if group_id not in self.bot_message_ids:
                        self.bot_message_ids[group_id] = set()
                    self.bot_message_ids[group_id].add(result[1]['message_id'])
            else:
                # 图片生成失败时的备用文字
                theme_line = f"【主题】: {theme}\n" if theme else ""
                game_info = (
                    f"▶️-> 游戏开始！{self._get_random_emoji('excited')} (生成耗时: {duration:.2f} 秒)\n"
                    f"【故事ID】: {story_record.id}\n"
                    f"{theme_line}"
                    f"🥣-> 汤面是：\n{display_soup_face}\n\n"
                    f"🎯-> 需要猜中 {len(all_key_points)} 个关键点或完整故事情节\n"
                    f"请使用 #seat <你的问题> 或 #st <你的问题> 来提问"
                )
                result = self.util.send_group_msg(self.auth, group_id, f"[seat] {game_info}")
                # 记录消息ID
                if result and isinstance(result, tuple) and result[0] and isinstance(result[1], dict) and 'message_id' in result[1]:
                    self.active_games[group_id]["game_message_ids"].add(result[1]['message_id'])
                    if group_id not in self.bot_message_ids:
                        self.bot_message_ids[group_id] = set()
                    self.bot_message_ids[group_id].add(result[1]['message_id'])
        else:
            # 失败消息也用图片
            img_content = f"创作失败...看来灵感缪斯今天罢工了 {self._get_random_emoji('sad')}\n耗时: {duration:.2f} 秒\n\n请稍后再试"
            img_base64 = self._create_game_image(
                f"❌ 创作失败 {self._get_random_emoji('sad')}",
                img_content,
                "请稍后重试",
                "red"
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                self.util.send_group_msg(
                    self.auth, group_id, 
                    f"[seat] 创作失败...看来灵感缪斯今天罢工了 {self._get_random_emoji('sad')} (耗时: {duration:.2f} 秒)。请稍后再试。"
                )

    
    def _end_game(self, group_id, reason=""):
        """结束游戏（合并所有信息到一张图片）"""
        if group_id in self.active_games:
            story_id = self.active_games[group_id]['story_id']
            guess_history = self.active_games[group_id]['guess_history']
            theme = self.active_games[group_id].get('theme')
            guessed_keys = self.active_games[group_id]['guessed_keys']
            guess_counts = self.active_games[group_id]['guess_counts']
            start_time = self.active_games[group_id]['start_time']
            
            db_session = self.Session()
            try:
                story = db_session.query(StoryCollection).filter_by(id=story_id).first()
                if story:
                    # 计算游戏时长
                    game_duration = datetime.now() - start_time
                    duration_minutes = int(game_duration.total_seconds() / 60)
                    
                    # 构建主要内容
                    theme_info = f"主题：{theme}\n" if theme else ""
                    img_content = (
                        f"{reason}\n\n"
                        f"{theme_info}"
                        f"🍲 汤底揭晓：\n{story.soup_bottom}\n\n"
                        f"📊 游戏统计：\n"
                        f"• 游戏时长：{duration_minutes} 分钟\n"
                        f"• 总猜测次数：{len(guess_history)} 次\n"
                        f"• 猜中关键点：{len(guessed_keys)}/{len([kp.strip() for kp in story.key_points.split(',') if kp])}\n"
                    )
                    
                    # 添加排行榜
                    if guess_counts:
                        sorted_players = sorted(guess_counts.items(), key=lambda x: x[1], reverse=True)
                        img_content += f"\n🏅 猜测排行榜 {self._get_random_emoji('happy')}：\n"
                        for i, (player_id, count) in enumerate(sorted_players[:5], 1):
                            # 从历史记录中找到玩家名字
                            player_name = str(player_id)
                            for record in guess_history:
                                if record['user_id'] == player_id:
                                    player_name = record['user_name']
                                    break
                            img_content += f"{i}. {player_name} - {count}次\n"
                    
                    # 构建小字文本（完整的关键点和猜测历史）
                    small_text = f"🔑 所有关键点：{story.key_points}\n"
                    if guessed_keys:
                        small_text += f"✅ 已猜中的：{', '.join(sorted(guessed_keys))}\n"
                    
                    small_text += "\n📝 最近猜测记录：\n"
                    recent_guesses = guess_history[-10:]  # 最多显示10条
                    for guess in recent_guesses:
                        time_str = guess['timestamp'].strftime("%H:%M")
                        truncated_question = guess['question'][:40] + ('...' if len(guess['question']) > 40 else '')
                        small_text += f"[{time_str}] {guess['user_name']}: {truncated_question}\n"
                    
                    # 创建结束图片
                    img_base64 = self._create_game_image(
                        f"🎉 游戏结束 {self._get_random_emoji('excited')}",
                        img_content,
                        f"感谢参与！• 故事ID: {story_id}",
                        "red",
                        small_text
                    )
                    
                    if img_base64:
                        image_cq = f"[CQ:image,file=base64://{img_base64}]"
                        self.util.send_group_msg(self.auth, group_id, image_cq)
                    else:
                        # 备用文字版本
                        theme_line = f"【主题】: {theme}\n" if theme else ""
                        end_content = (
                            f"{reason}\n"
                            f"🎉 游戏结束！{self._get_random_emoji('excited')}\n"
                            f"{theme_line}"
                            f"🍲 汤底是：\n{story.soup_bottom}\n\n"
                            f"📊 统计：时长{duration_minutes}分钟，共{len(guess_history)}次猜测"
                        )
                        self.util.send_group_msg(self.auth, group_id, f"[seat] {end_content}")
            finally:
                db_session.close()
            
            # 清理游戏状态和消息ID记录
            self.active_games.pop(group_id, None)
            if group_id in self.bot_message_ids:
                del self.bot_message_ids[group_id]
            
            

    def _handle_help(self, group_id):
        """显示帮助信息 - 使用图片"""
        help_content = (
            f"📖 海龟汤游戏指南 📖 {self._get_random_emoji('happy')}\n\n"
            "核心指令：\n"
            "🔹 #seat start [主题] - 开始新游戏（可指定主题）\n"
            "🔹 #st start [主题] - 快捷命令\n"
            "🔹 #seat <问题> - 提问\n"
            "🔹 #st <问题> - 快捷提问\n"
            "🔹 #seat end - 结束游戏\n"
            "🔹 #seat hint - 获取提示\n"
            "🔹 #seat recap - 查看状态\n"
            "🔹 #seat help - 显示帮助\n\n"
            "胜利条件：\n"
            "🏆 猜中所有关键点或完整描述故事真相\n\n"
            "新增特色：\n"
            "✨ 相似度评分 - 使用AI计算推理相似度\n"
            "✨ 连续评分系统 - 0-100分精准评价\n"
            "✨ 完整信息展示 - 包含汤面和猜测记录\n"
            "✨ 趣味颜文字 - 让游戏更生动有趣\n\n"
            "示例：\n"
            "#seat start 医院\n"
            "#st 他是医生吗？\n"
            "#st 手术，意外，死亡"
        )
        
        img_base64 = self._create_game_image(
            f"🐢 海龟汤游戏帮助 {self._get_random_emoji('neutral')}",
            help_content,
            f"v{plugin_version} • 更智能的海龟汤平台",
            "green"
        )
        
        if img_base64:
            image_cq = f"[CQ:image,file=base64://{img_base64}]"
            self.util.send_group_msg(self.auth, group_id, image_cq)
        else:
            # 备用文字版本
            help_text = f"""[seat] 📖 海龟汤游戏帮助菜单 (v{plugin_version}) 📖 {self._get_random_emoji('happy')}
一个更智能、更公平的海龟汤平台！

--- 核心指令 ---
🔹 #seat start [主题] 或 #st start [主题]
   开始游戏，可选指定主题（如：#seat start 医院）
🔹 #seat <你的问题> 或 #st <你的问题>
   在游戏中提问，例如：#st 他是自杀吗？
🔹 #seat end 或 #st end
   中断当前游戏，并立即查看汤底
🔹 #seat hint 或 #st hint
   获取一个关键点提示 (每局限一次)
🔹 #seat recap 或 #st recap
   重新显示当前汤面和游戏状态
🔹 #seat help 或 #st help
   显示此帮助菜单

--- 胜利条件 ---
🏆 猜中所有关键点 或 完整描述故事真相

--- 新特性 ---
✨ 相似度评分系统，0-100分连续评分
✨ 完整信息展示，包含汤面和历史记录
✨ 趣味颜文字，让游戏更生动"""
            self.util.send_group_msg(self.auth, group_id, help_text)

    def _handle_hint(self, group_id, sender):
        """处理提示请求 - 使用图片"""
        if group_id not in self.active_games:
            img_content = f"当前没有进行中的游戏 {self._get_random_emoji('thinking')}\n\n请使用 #seat start 或 #st start 开始新游戏"
            img_base64 = self._create_game_image(
                f"❌ 无游戏进行中 {self._get_random_emoji('sad')}",
                img_content,
                "",
                "red"
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                self.util.send_group_msg(self.auth, group_id, f"[seat] 没有正在进行的游戏。{self._get_random_emoji('sad')}")
            return
            
        state = self.active_games[group_id]
        sender_name = sender.get('card') or sender.get('nickname') or str(sender.get('user_id'))
        
        if state['hints_used'] > 0:
            img_content = f"玩家：{sender_name}\n\n本局的提示机会已经用完了！{self._get_random_emoji('sad')}\n\n请继续努力猜测吧！{self._get_random_emoji('thinking')}"
            img_base64 = self._create_game_image(
                f"💡 提示已用尽 {self._get_random_emoji('neutral')}",
                img_content,
                f"故事ID: {state['story_id']}",
                "red"
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                self.util.send_group_msg(self.auth, group_id, f"[seat] @{sender_name} 本局的提示机会已经用完啦！{self._get_random_emoji('sad')}")
            return

        db_session = self.Session()
        try:
            story = db_session.query(StoryCollection).filter_by(id=state['story_id']).first()
            if not story:
                return
                
            key_points = [kp.strip() for kp in story.key_points.split(',') if kp]
            unguessed_keys = [k for k in key_points if k and k not in state['guessed_keys']]
            
            if not unguessed_keys:
                img_content = f"玩家：{sender_name}\n\n所有关键点都已被猜到！{self._get_random_emoji('excited')}\n\n试试直接描述完整故事吧！{self._get_random_emoji('happy')}"
                img_base64 = self._create_game_image(
                    f"✅ 关键点已全部猜中 {self._get_random_emoji('success')}",
                    img_content,
                    f"故事ID: {state['story_id']}",
                    "green"
                )
                
                if img_base64:
                    image_cq = f"[CQ:image,file=base64://{img_base64}]"
                    self.util.send_group_msg(self.auth, group_id, image_cq)
                else:
                    self.util.send_group_msg(self.auth, group_id, f"[seat] @{sender_name} 所有关键点都已被猜到，试试直接描述完整故事吧！{self._get_random_emoji('happy')}")
                return
                
            hint = random.choice(unguessed_keys)
            state['hints_used'] += 1
            progress = len(state['guessed_keys'])
            total = len(key_points)
            
            img_content = (
                f"玩家：{sender_name}\n\n"
                f"提示关键词：{hint} {self._get_random_emoji('thinking')}\n\n"
                f"请朝这个方向思考...\n\n"
                f"当前进度：{progress}/{total} 个关键点"
            )
            
            img_base64 = self._create_game_image(
                f"💡 获得提示 {self._get_random_emoji('neutral')}",
                img_content,
                f"提示已用完 • 故事ID: {state['story_id']}",
                "blue"
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                # 备用文字版本
                hint_content = (
                    f"💡 @{sender_name} 收到一条提示：请试着朝「{hint}」的方向思考。{self._get_random_emoji('thinking')}\n"
                    f"📊 当前进度：{progress}/{total} 个关键点"
                )
                self.util.send_group_msg(self.auth, group_id, f"[seat] {hint_content}")
                
        finally:
            db_session.close()

    def _handle_recap(self, group_id):
        """重新输出汤面 - 使用图片"""
        if group_id not in self.active_games:
            img_content = f"当前没有进行中的游戏 {self._get_random_emoji('thinking')}\n\n使用 #seat start 或 #st start 开始新游戏"
            img_base64 = self._create_game_image(
                f"❌ 无游戏进行中 {self._get_random_emoji('sad')}",
                img_content,
                "",
                "red"
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                self.util.send_group_msg(self.auth, group_id, f"[seat] 当前没有进行中的游戏。使用 #seat start 开始新游戏。{self._get_random_emoji('sad')}")
            return
            
        state = self.active_games[group_id]
        db_session = self.Session()
        try:
            story = db_session.query(StoryCollection).filter_by(id=state['story_id']).first()
            if not story:
                self.util.send_group_msg(self.auth, group_id, f"[seat] 错误：找不到当前游戏的故事记录。{self._get_random_emoji('sad')}")
                return
                
            all_key_points = [kp.strip() for kp in story.key_points.split(',') if kp]
            progress = len(state['guessed_keys'])
            total = len(all_key_points)
            
            # 计算游戏时长
            game_duration = datetime.now() - state['start_time']
            duration_minutes = int(game_duration.total_seconds() / 60)
            
            # 处理过长的汤面
            display_soup_face = story.soup_face
            if len(display_soup_face) > 400:
                display_soup_face = display_soup_face[:400] + "..."
            
            theme_info = f"主题：{state.get('theme')}\n" if state.get('theme') else ""
            img_content = (
                f"故事ID: {state['story_id']} • 时长: {duration_minutes}分钟\n"
                f"{theme_info}\n"
                f"🥣 汤面：\n{display_soup_face}\n\n"
                f"📊 进度：{progress}/{total} ({progress/total*100:.0f}%)\n"
                f"总猜测：{len(state['guess_history'])}次\n"
                f"提示：{'已用完' if state['hints_used'] > 0 else '可用'}"
            )
            
            # 构建小字文本
            small_text = ""
            if state['guessed_keys']:
                small_text += f"✅ 已猜中：{', '.join(sorted(state['guessed_keys']))}\n"
            
            # 添加最近的猜测历史
            if state['guess_history']:
                small_text += "\n📝 最近猜测：\n"
                recent_guesses = state['guess_history'][-6:]  # 最多显示6条
                for guess in recent_guesses:
                    time_str = guess['timestamp'].strftime("%H:%M")
                    truncated_question = guess['question'][:35] + ('...' if len(guess['question']) > 35 else '')
                    small_text += f"[{time_str}] {guess['user_name']}: {truncated_question}\n"
            
            img_base64 = self._create_game_image(
                f"📖 游戏状态回顾 {self._get_random_emoji('neutral')}",
                img_content,
                f"继续加油！使用 #seat <问题> 或 #st <问题> 提问",
                "blue",
                small_text
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                # 备用文字版本
                theme_info = f"主题：{state.get('theme')}\n" if state.get('theme') else ""
                recap_content = (
                    f"📖 当前游戏状态回顾 {self._get_random_emoji('neutral')}\n"
                    f"【故事ID】: {state['story_id']}\n"
                    f"{theme_info}"
                    f"【游戏时长】: {duration_minutes} 分钟\n\n"
                    f"🥣 汤面：\n{display_soup_face}\n\n"
                    f"📊 进度：{progress}/{total} 个关键点 ({progress/total*100:.0f}%)\n"
                    f"💡 提示使用：{'已用完' if state['hints_used'] > 0 else '未使用'}\n"
                    f"🔢 总猜测次数：{len(state['guess_history'])}\n\n"
                    f"继续使用 #seat <问题> 或 #st <问题> 进行提问"
                )
                
                if state['guessed_keys']:
                    recap_content += f"\n✅ 已猜中关键点：{', '.join(state['guessed_keys'])}"
                
                self.util.send_group_msg(self.auth, group_id, f"[seat] {recap_content}")
                
        finally:
            db_session.close()

    def _check_timeout(self, group_id):
        """检查游戏超时"""
        if group_id in self.active_games:
            state = self.active_games[group_id]
            if datetime.now() > state["start_time"] + timedelta(minutes=self.game_timeout_minutes):
                self.log.info(f"群 {group_id} 的海龟汤游戏超时，自动结束。")
                self._end_game(group_id, f"⌛ 时间到！本次游戏已超过 {self.game_timeout_minutes} 分钟，自动结束。{self._get_random_emoji('neutral')}")

    def _handle_list_stories(self, group_id, page=1):
        """调试：列出故事库 - 使用图片"""
        if not self.db_ready:
            self.util.send_group_msg(self.auth, group_id, f"[seat] 数据库未就绪。{self._get_random_emoji('sad')}")
            return
            
        db_session = self.Session()
        try:
            total_stories = db_session.query(func.count(StoryCollection.id)).scalar()
            if total_stories == 0:
                img_content = f"故事库目前是空的 {self._get_random_emoji('sad')}\n\n使用 #seat new 创建新故事"
                img_base64 = self._create_game_image(
                    f"📚 故事库 {self._get_random_emoji('neutral')}",
                    img_content,
                    "调试模式",
                    "blue"
                )
                
                if img_base64:
                    image_cq = f"[CQ:image,file=base64://{img_base64}]"
                    self.util.send_group_msg(self.auth, group_id, image_cq)
                else:
                    self.util.send_group_msg(self.auth, group_id, f"[seat] 调试：故事库是空的。{self._get_random_emoji('sad')}")
                return

            total_pages = (total_stories + self.stories_per_page - 1) // self.stories_per_page
            if not (1 <= page <= total_pages):
                self.util.send_group_msg(self.auth, group_id, f"[seat] 调试：页码无效。请输入1到{total_pages}之间的页码。{self._get_random_emoji('thinking')}")
                return

            offset = (page - 1) * self.stories_per_page
            stories = db_session.query(StoryCollection).order_by(StoryCollection.id.desc()).offset(offset).limit(self.stories_per_page).all()
            
            content_lines = []
            for story in stories:
                theme_tag = f"[{story.theme}] " if story.theme else ""
                content_lines.append(f"🆔 {story.id} {theme_tag}\n{story.soup_face[:350]}...\n")
            
            img_content = "\n".join(content_lines)
            img_base64 = self._create_game_image(
                f"📚 故事库 (第{page}/{total_pages}页) {self._get_random_emoji('neutral')}",
                img_content,
                f"共 {total_stories} 个故事 • 调试模式",
                "blue"
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                # 备用文字版本
                response_lines = [f"[seat] --- 📖 调试：故事库 (第 {page}/{total_pages} 页) 📖 ---"]
                for story in stories:
                    theme_tag = f"[{story.theme}] " if story.theme else ""
                    response_lines.append(f"🆔 {story.id} {theme_tag}| {story.soup_face[:30]}...")
                self.util.send_group_msg(self.auth, group_id, "\n".join(response_lines))
        finally:
            db_session.close()

    def _calculate_similarity_advanced(self, question, soup_bottom, key_points):
        """使用多种算法计算相似度分数"""
        try:
            # 1. 基础embedding相似度
            question_embedding = self._get_embedding(question)
            soup_embedding = self._get_embedding(soup_bottom)

            if question_embedding is not None and soup_embedding is not None:
                # 余弦相似度
                vec1_norm = question_embedding / np.linalg.norm(question_embedding)
                vec2_norm = soup_embedding / np.linalg.norm(soup_embedding)
                cosine_similarity = np.dot(vec1_norm, vec2_norm)
                base_score = int((cosine_similarity + 1) * 50)  # 0-100分
            else:
                base_score = 50

            # 2. 关键词匹配加分
            keyword_bonus = 0
            question_lower = question.lower()
            for keyword in key_points.split(','):
                keyword = keyword.strip().lower()
                if keyword and keyword in question_lower:
                    keyword_bonus += 10  # 每个关键词加10分

            # 3. 问题长度和复杂度调整
            length_factor = min(len(question) / 100, 1.0)  # 长度因子，最多1.0
            complexity_bonus = length_factor * 10  # 最多加10分

            # 4. 计算最终分数
            final_score = min(100, base_score + keyword_bonus + complexity_bonus)

            # 5. 添加一些随机性（±5分）
            import random
            final_score += random.randint(-5, 5)
            final_score = max(0, min(100, final_score))

            return final_score

        except Exception as e:
            self.log.error(f"高级相似度计算失败: {e}")
            return 50  # 默认分数

    def _threaded_debug_new_story(self, group_id, user_id):
        """调试：创建新故事"""
        self.util.send_group_msg(self.auth, group_id, f"[seat] 收到调试命令！正在为您创作一个新故事...{self._get_random_emoji('thinking')}(后台处理中)")
        start_time = time.time()
        story_record = self._generate_story_from_api(user_id)
        end_time = time.time()
        duration = end_time - start_time

        if story_record:
            img_content = (
                f"故事ID: {story_record.id}\n"
                f"生成耗时: {duration:.2f}秒\n\n"
                f"汤面：\n{story_record.soup_face}\n\n"
                f"关键点：{story_record.key_points}"
            )
            
            img_base64 = self._create_game_image(
                f"✅ 故事创作成功 {self._get_random_emoji('success')}",
                img_content,
                "调试模式",
                "green"
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                self.util.send_group_msg(
                    self.auth, group_id,
                    f"[seat] ✅ 调试：故事创作成功！{self._get_random_emoji('happy')} (耗时: {duration:.2f} 秒)\n\n"
                    f"【故事ID】: {story_record.id}\n"
                    f"【汤面】: {story_record.soup_face}\n"
                    f"【关键点】: {story_record.key_points}"
                )
        else:
            img_content = f"故事创作失败 {self._get_random_emoji('sad')}\n耗时: {duration:.2f}秒\n\n请稍后重试"
            img_base64 = self._create_game_image(
                f"❌ 创作失败 {self._get_random_emoji('sad')}",
                img_content,
                "调试模式",
                "red"
            )
            
            if img_base64:
                image_cq = f"[CQ:image,file=base64://{img_base64}]"
                self.util.send_group_msg(self.auth, group_id, image_cq)
            else:
                self.util.send_group_msg(self.auth, group_id, f"[seat] ❌ 调试：故事创作失败 {self._get_random_emoji('sad')} (耗时: {duration:.2f} 秒)。")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender):
        """处理群消息"""
        # 记录原始消息
        self.log.debug(f"[group_message] 收到群消息 - 群号: {group_id}, 用户: {user_id}, 原始消息: {raw_message}")
        
        # 检查超时
        self._check_timeout(group_id)

        # 检查是否为插件指令，支持 #seat 和 #st
        clean_msg = raw_message.strip()
        self.log.debug(f"[group_message] 清理后的消息: {clean_msg}")
        
        # 检查是否包含引用回复
        import re
        reply_pattern = r'\[CQ:reply,id=(-?\d+)\]'
        reply_match = re.search(reply_pattern, clean_msg)
        
        if reply_match:
            self.log.info(f"[group_message] 检测到引用回复，reply_id: {reply_match.group(1)}")
        
        # 如果有引用回复，检查是否应该自动转换为提问
        if reply_match and not clean_msg.lower().startswith(('#seat', '#st')):
            reply_msg_id = int(reply_match.group(1))
            self.log.debug(f"[group_message] 引用消息ID: {reply_msg_id}, 不是以#seat或#st开头")
            
            # 检查是否在游戏中
            if group_id in self.active_games:
                self.log.debug(f"[group_message] 群 {group_id} 有游戏进行中")
                
                # 检查被引用的消息是否是游戏期间机器人发送的
                game_msg_ids = self.active_games[group_id].get("game_message_ids", set())
                bot_msg_ids = self.bot_message_ids.get(group_id, set())
                
                self.log.debug(f"[group_message] 游戏消息IDs: {game_msg_ids}")
                self.log.debug(f"[group_message] 机器人消息IDs: {bot_msg_ids}")
                
                # 只有当引用的是游戏期间机器人的消息时才自动转换
                if reply_msg_id in game_msg_ids or reply_msg_id in bot_msg_ids:
                    self.log.info(f"[group_message] 引用的是游戏消息，进行自动转换")
                    
                    # 移除所有CQ码，只保留纯文本
                    cq_pattern = r'\[CQ:[^\]]+\]'
                    actual_content = re.sub(cq_pattern, '', clean_msg).strip()
                    
                    self.log.debug(f"[group_message] 移除CQ码后的内容: {actual_content}")
                    
                    # 如果有实际内容，则添加 #st 前缀
                    if actual_content:
                        clean_msg = '#st ' + actual_content
                        self.log.info(f"[group_message] 自动转换为: {clean_msg}")
                    else:
                        # 如果引用回复后没有内容，忽略
                        self.log.debug(f"[group_message] 引用回复后无实际内容，忽略")
                        return False
                else:
                    # 引用的不是游戏消息，忽略
                    self.log.debug(f"[group_message] 引用的不是游戏消息，忽略")
                    return False
            else:
                # 没有游戏进行中，忽略引用回复
                self.log.debug(f"[group_message] 群 {group_id} 没有游戏进行中，忽略引用回复")
                return False
        
        # 将 #st 转换为 #seat
        if clean_msg.lower().startswith('#st'):
            original_msg = clean_msg
            clean_msg = '#seat' + clean_msg[3:]
            self.log.info(f"[group_message] 将 {original_msg} 转换为 {clean_msg}")
        
        if not clean_msg.lower().startswith('#seat'):
            self.log.debug(f"[group_message] 消息不是以#seat开头，忽略")
            return False

        self.log.info(f"[group_message] 检测到#seat命令: {clean_msg}")

        # 解析指令 - 移除所有CQ码再解析
        cq_pattern = r'\[CQ:[^\]]+\]'
        clean_msg_no_cq = re.sub(cq_pattern, '', clean_msg).strip()
        
        self.log.debug(f"[group_message] 移除所有CQ码后: {clean_msg_no_cq}")
        
        parts = clean_msg_no_cq.split(maxsplit=1)
        content = parts[1] if len(parts) > 1 else ""
        
        self.log.debug(f"[group_message] 解析结果 - parts: {parts}, content: '{content}'")
        
        # 先检查是否是特殊命令
        content_parts = content.split() if content else []
        first_word = content_parts[0].lower() if content_parts else ""
        
        # 定义有效的命令列表
        valid_commands = ['start', 'help', 'recap', 'end', 'hint', 'new', 'list']
        
        # 判断是否是命令
        is_command = first_word in valid_commands
        
        self.log.info(f"[group_message] 第一个词: '{first_word}', 是否为命令: {is_command}")

        # 处理单独的 #seat 或 #seat help
        if not content or first_word == 'help':
            self.log.info(f"[group_message] 处理help命令")
            self._handle_help(group_id)
            return True
        
        # 处理特定命令
        if is_command:
            main_command = first_word
            self.log.info(f"[group_message] 识别到命令: {main_command}")
            
            if main_command == 'start':
                self.log.info(f"[group_message] 处理start命令")
                if group_id in self.active_games:
                    self.log.warning(f"[group_message] 群 {group_id} 已有游戏进行中")
                    img_content = "游戏已在进行中！\n\n请先使用 #seat end 或 #st end 结束当前游戏"
                    img_base64 = self._create_game_image(
                        "⚠️ 游戏进行中",
                        img_content,
                        f"故事ID: {self.active_games[group_id]['story_id']}",
                        "red"
                    )
                    
                    if img_base64:
                        image_cq = f"[CQ:image,file=base64://{img_base64}]"
                        self.util.send_group_msg(self.auth, group_id, image_cq)
                    else:
                        self.util.send_group_msg(self.auth, group_id, "[seat] 游戏已在进行中！请先使用 #seat end 结束当前游戏。")
                else:
                    # 检查是否有主题参数
                    theme = None
                    if len(content_parts) > 1:
                        theme = ' '.join(content_parts[1:])
                        # 限制主题长度
                        if len(theme) > 500:
                            theme = theme[:500]
                        self.log.info(f"[group_message] 开始游戏，主题: {theme}")
                    
                    # 传递 message_id 和主题
                    thread = threading.Thread(target=self._threaded_create_and_start_game, args=(group_id, user_id, message_id, theme))
                    thread.start()
                    self.log.info(f"[group_message] 启动游戏创建线程")
                return True

            elif main_command == 'recap':
                self.log.info(f"[group_message] 处理recap命令")
                self._handle_recap(group_id)
                return True

            elif main_command == 'new':  # 调试指令
                self.log.info(f"[group_message] 处理new命令（调试）")
                thread = threading.Thread(target=self._threaded_debug_new_story, args=(group_id, user_id))
                thread.start()
                return True

            elif main_command == 'list':  # 调试指令
                self.log.info(f"[group_message] 处理list命令（调试）")
                page = 1
                if len(content_parts) > 1 and content_parts[1].isdigit():
                    page = int(content_parts[1])
                self._handle_list_stories(group_id, page=page)
                return True

            elif main_command == 'end':
                self.log.info(f"[group_message] 处理end命令")
                if group_id in self.active_games:
                    sender_name = sender.get('card') or sender.get('nickname') or str(user_id)
                    self._end_game(group_id, f"应玩家 @{sender_name} 的要求，游戏提前结束。")
                else:
                    self.log.warning(f"[group_message] 没有游戏进行中，无法结束")
                    self.util.send_group_msg(self.auth, group_id, f"[seat] 当前没有游戏进行中。{self._get_random_emoji('thinking')}")
                return True

            elif main_command == 'hint':
                self.log.info(f"[group_message] 处理hint命令")
                self._handle_hint(group_id, sender)
                return True
        
        # 如果不是命令，且游戏进行中，则当作提问处理
        elif group_id in self.active_games and content:
            self.log.info(f"[group_message] 群 {group_id} 游戏进行中，将内容作为提问处理: {content}")
            thread = threading.Thread(target=self._threaded_get_judge_response, args=(group_id, user_id, content, sender, message_id))
            thread.start()
            self.log.info(f"[group_message] 启动判断线程")
            return True
        
        # 没有游戏进行中，但输入了非命令内容
        else:
            self.log.warning(f"[group_message] 没有游戏进行中，忽略非命令内容")
            self.util.send_group_msg(self.auth, group_id, f"[seat] 当前没有游戏进行中。使用 #seat start 开始新游戏。{self._get_random_emoji('thinking')}")
            return True

        return False