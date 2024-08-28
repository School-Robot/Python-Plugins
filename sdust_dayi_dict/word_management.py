# word_management.py

import os
import uuid
import base64
import random
import re
from urllib.parse import unquote
from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker
from .models import Base, Word, Admin, Image, Alias
from .image_downloader import download_image
from .config import get_default_admins, get_super_admin, save_config, get_database_url

class WordManagement:
    def __init__(self, plugin_dir, config):
        self.pic_dir = os.path.join(plugin_dir, 'data', 'pic')
        os.makedirs(self.pic_dir, exist_ok=True)
        self.config = config
        self.plugin_dir = plugin_dir
        self.database_url = get_database_url(config)
        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.init_default_admins()

    def init_default_admins(self):
        default_admins = get_default_admins(self.config)
        super_admin = get_super_admin(self.config)
        session = self.Session()
        try:
            for admin in default_admins:
                session.merge(Admin(qq_number=admin, level=1))
            if super_admin:
                session.merge(Admin(qq_number=super_admin, level=5))
            session.commit()
        finally:
            session.close()

    def add_alias(self, group_id, alias, command):
        session = self.Session()
        try:
            new_alias = Alias(group_id=group_id, alias=alias, command=command)
            session.add(new_alias)
            session.commit()
        finally:
            session.close()

    def delete_alias(self, group_id, alias):
        session = self.Session()
        try:
            session.query(Alias).filter_by(group_id=group_id, alias=alias).delete()
            session.commit()
        finally:
            session.close()

    def get_alias(self, group_id, alias):
        session = self.Session()
        try:
            result = session.query(Alias).filter_by(group_id=group_id, alias=alias).first()
            return result.command if result else None
        finally:
            session.close()

    def list_aliases(self, group_id):
        session = self.Session()
        try:
            return [(alias.alias, alias.command) for alias in session.query(Alias).filter_by(group_id=group_id)]
        finally:
            session.close()

    def add_word(self, group_id, question, answer):
      try:
        # 确保 answer 是字符串
        if not isinstance(answer, str):
            answer = str(answer)
        
        processed_answer = self.process_image_cq(answer)
        session = self.Session()
        try:
            word = Word(group_id=group_id, question=question, answer=processed_answer)
            session.add(word)
            session.commit()
            print(f"Added word: question={question}, processed_answer={processed_answer}")
        finally:
            session.close()
      except Exception as e:
        print(f"Error in add_word: {e}")
        # 可以选择在这里重新抛出异常，或者返回一个错误标志
        raise

    def delete_word(self, group_id, question):
        session = self.Session()
        try:
            session.query(Word).filter_by(group_id=group_id, question=question).delete()
            session.commit()
        finally:
            session.close()

    def get_all_words(self, group_id):
        session = self.Session()
        try:
            return [(word.question, word.answer) for word in session.query(Word).filter_by(group_id=group_id)]
        finally:
            session.close()

    def get_all_answers(self, group_id, question):
        session = self.Session()
        try:
            words = session.query(Word).filter_by(group_id=group_id, question=question).all()
            return [word.answer for word in words]
        finally:
            session.close()
        
    def add_admin(self, qq_number, level):
        session = self.Session()
        try:
            admin = Admin(qq_number=str(qq_number), level=level)
            session.merge(admin)
            session.commit()
        finally:
            session.close()
        
        default_admins = get_default_admins(self.config)
        if str(qq_number) not in default_admins:
            default_admins.append(str(qq_number))
            self.config.set("WordManagement", "default_admins", ",".join(default_admins))
            save_config(self.config, self.plugin_dir)

    def get_admin_level(self, qq_number):
        session = self.Session()
        try:
            admin = session.query(Admin).filter_by(qq_number=str(qq_number)).first()
            return admin.level if admin else 0
        finally:
            session.close()
            
    def get_all_alias_definitions(self, group_id, alias):
        session = self.Session()
        try:
            aliases = session.query(Alias).filter_by(group_id=group_id, alias=alias).all()
            return [alias.command for alias in aliases]
        finally:
            session.close()

    def process_image_cq(self, text):
        def replace_image_url(match):
            full_cq = match.group(0)
            url_match = re.search(r'file=(https?://[^,\]]+)', full_cq)
            if url_match:
                url = unquote(url_match.group(1))
                image_uuid = self.download_and_save_image(url)
                return f'$$<image:{image_uuid}>$$'
            return full_cq

        pattern = r'\[CQ:image[^\]]+\]'
        return re.sub(pattern, replace_image_url, text)

    def download_and_save_image(self, url):
        session = self.Session()
        try:
            existing_image = session.query(Image).filter_by(url=url).first()
            if existing_image:
                return os.path.basename(existing_image.local_path)

            image_uuid = str(uuid.uuid4())
            filename = f"{image_uuid}.jpg"
            local_path = os.path.join(self.pic_dir, filename)

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            if download_image(url, local_path):
                new_image = Image(url=url, local_path=local_path)
                session.add(new_image)
                session.commit()
                return image_uuid
        except Exception as e:
            print(f"An error occurred while downloading image: {e}")
        finally:
            session.close()
        
        return None

    def get_image_base64(self, local_path):
        full_path = os.path.join(self.pic_dir, local_path)
        if os.path.exists(full_path):
            with open(full_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        return None

    def search_words(self, group_id, keyword):
        session = self.Session()
        try:
            return session.query(Word.question, Word.answer).filter(
                Word.group_id == group_id,
                or_(Word.question.like(f'%{keyword}%'), Word.answer.like(f'%{keyword}%'))
            ).all()
        finally:
            session.close()

    def update_word(self, group_id, question, new_answer):
        processed_answer = self.process_image_cq(new_answer)
        session = self.Session()
        try:
            word = session.query(Word).filter_by(group_id=group_id, question=question).first()
            if word:
                word.answer = processed_answer
                session.commit()
        finally:
            session.close()

    def get_admin_list(self):
        session = self.Session()
        try:
            return [(admin.qq_number, admin.level) for admin in session.query(Admin).order_by(Admin.level.desc())]
        finally:
            session.close()

    def remove_admin(self, qq_number):
        session = self.Session()
        try:
            session.query(Admin).filter_by(qq_number=str(qq_number)).delete()
            session.commit()
        finally:
            session.close()

        default_admins = get_default_admins(self.config)
        if str(qq_number) in default_admins:
            default_admins.remove(str(qq_number))
            self.config.set("WordManagement", "default_admins", ",".join(default_admins))
            save_config(self.config, self.plugin_dir)

    def clean_unused_images(self):
        session = self.Session()
        try:
            all_images = session.query(Image).all()
            for image in all_images:
                full_path = os.path.join(self.pic_dir, image.local_path)
                if not os.path.exists(full_path):
                    session.delete(image)
            session.commit()
        finally:
            session.close()

    def get_word_count(self, group_id=None):
        session = self.Session()
        try:
            query = session.query(func.count(Word.id))
            if group_id:
                query = query.filter_by(group_id=group_id)
            return query.scalar()
        finally:
            session.close()

    def get_image_count(self):
        session = self.Session()
        try:
            return session.query(func.count(Image.id)).scalar()
        finally:
            session.close()

    def check_and_respond(self, group_id, message, plugin):
      session = self.Session()
      try:
        # 首先检查是否有匹配的别名
        aliases = session.query(Alias).filter_by(group_id=group_id, alias=message).all()
        if aliases:
            # 如果有多个匹配的别名，随机选择一个
            chosen_alias = random.choice(aliases)
            response = self.process_alias_command(group_id, chosen_alias.command, plugin)
            
            # 如果有多个别名，添加提示
            if len(aliases) > 1:
                response = f"[提示：该别名有 {len(aliases)} 个定义]\n{response}"
            
            return response

        # 如果不是别名，则查找匹配的词条
        words = session.query(Word).filter_by(group_id=group_id, question=message).all()
        if not words:
            return None

        # 如果有多个匹配的词条，随机选择一个
        chosen_word = random.choice(words)
        response = self.process_answer(chosen_word.answer, plugin)

        # 如果有多个回复，添加提示
        if len(words) > 1:
            response = f"[提示：该问题有 {len(words)} 个回答]\n{response}"

        return response
      finally:
        session.close()

    def process_alias_command(self, group_id, command, plugin):
        pattern = r'\$\$<command:(.*?)>\$\$'
        def replace_command(match):
            cmd = match.group(1)
            result, response = plugin.execute_command(None, group_id, None, cmd)
            return response if response else ''

        return re.sub(pattern, replace_command, command)

    def process_answer(self, answer, plugin):
        # 处理答案中的命令
        command_pattern = r'\$\$<command:(.*?)>\$\$'
        def replace_command(match):
            cmd = match.group(1)
            result, response = plugin.execute_command(None, None, None, cmd)
            return response if response else ''

        answer = re.sub(command_pattern, replace_command, answer)

        # 处理图片
        img_pattern = r'\$\$<image:(.*?)>\$\$'
        def replace_image(match):
            image_uuid = match.group(1)
            img_path = os.path.join(self.pic_dir, f"{image_uuid}.jpg")
            if os.path.isfile(img_path):
                with open(img_path, "rb") as image_file:
                    img_str = base64.b64encode(image_file.read()).decode('utf-8')
                return f'[CQ:image,file=base64://{img_str}]'
            else:
                print(f"Image file not found: {img_path}")
            return ''

        return re.sub(img_pattern, replace_image, answer)

    def regex_search(self, group_id, pattern):
        session = self.Session()
        try:
            all_words = session.query(Word).filter_by(group_id=group_id).all()
            matches = []
            for word in all_words:
                if re.search(pattern, word.question) or re.search(pattern, word.answer):
                    matches.append((word.question, word.answer))
            return matches
        finally:
            session.close()

    def is_super_admin(self, qq_number):
        return str(qq_number) == get_super_admin(self.config)

    def get_questions(self, group_id, question_id=None):
        session = self.Session()
        try:
            query = session.query(Word.id, Word.question).filter_by(group_id=group_id)
            if question_id == 'all':
                return query.order_by(Word.id).all()
            elif question_id:
                return query.filter_by(id=question_id).all()
            else:
                return []
        finally:
            session.close()

    def get_pic_directory_size(self):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.pic_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def get_database_info(self):
        return self.database_url