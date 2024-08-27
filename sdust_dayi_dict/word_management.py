#word_management.py
import sqlite3
import os
import uuid
import base64
import threading
import re
from .image_downloader import download_image
from .config import get_default_admins, get_super_admin, save_config
from urllib.parse import urlparse, unquote

class WordManagement:
    def __init__(self, plugin_dir, config):
        self.db_path = os.path.join(plugin_dir, 'data', 'word_management.db')
        self.pic_dir = os.path.join(plugin_dir, 'data', 'pic')
        os.makedirs(self.pic_dir, exist_ok=True)
        self.local = threading.local()
        self.config = config
        self.plugin_dir = plugin_dir
        self.create_tables()
        self.init_default_admins()

    def get_conn(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path)
        return self.local.conn

    def create_tables(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS words
        (id INTEGER PRIMARY KEY, group_id TEXT, question TEXT, answer TEXT)
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins
        (id INTEGER PRIMARY KEY, qq_number TEXT, level INTEGER)
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS images
        (id INTEGER PRIMARY KEY, url TEXT, local_path TEXT)
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS aliases
        (id INTEGER PRIMARY KEY, group_id TEXT, alias TEXT, command TEXT)
        ''')
        conn.commit()
        
    #别名
    def add_alias(self, group_id, alias, command):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO aliases (group_id, alias, command) VALUES (?, ?, ?)', (group_id, alias, command))
        conn.commit()

    def delete_alias(self, group_id, alias):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM aliases WHERE group_id = ? AND alias = ?', (group_id, alias))
        conn.commit()

    def get_alias(self, group_id, alias):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT command FROM aliases WHERE group_id = ? AND alias = ?', (group_id, alias))
        result = cursor.fetchone()
        return result[0] if result else None

    def list_aliases(self, group_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT alias, command FROM aliases WHERE group_id = ?', (group_id,))
        return cursor.fetchall()

    def init_default_admins(self):
        default_admins = get_default_admins(self.config)
        super_admin = get_super_admin(self.config)
        conn = self.get_conn()
        cursor = conn.cursor()
        for admin in default_admins:
            cursor.execute('INSERT OR IGNORE INTO admins (qq_number, level) VALUES (?, ?)', (admin, 1))
        if super_admin:
            cursor.execute('INSERT OR IGNORE INTO admins (qq_number, level) VALUES (?, ?)', (super_admin, 5))
        conn.commit()

    def add_word(self, group_id, question, answer):
        conn = self.get_conn()
        cursor = conn.cursor()
        processed_answer = self.process_image_cq(answer)
        cursor.execute('INSERT INTO words (group_id, question, answer) VALUES (?, ?, ?)', (group_id, question, processed_answer))
        conn.commit()
        print(f"Added word: question={question}, processed_answer={processed_answer}")

    def delete_word(self, group_id, question):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM words WHERE group_id = ? AND question = ?', (group_id, question))
        conn.commit()

    def get_all_words(self, group_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT question, answer FROM words WHERE group_id = ?', (group_id,))
        return cursor.fetchall()

    def add_admin(self, qq_number, level):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO admins (qq_number, level) VALUES (?, ?)', (str(qq_number), level))
        conn.commit()
        # Update config file
        default_admins = get_default_admins(self.config)
        if str(qq_number) not in default_admins:
            default_admins.append(str(qq_number))
            self.config.set("WordManagement", "default_admins", ",".join(default_admins))
            save_config(self.config, self.plugin_dir)

    def get_admin_level(self, qq_number):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT level FROM admins WHERE qq_number = ?', (str(qq_number),))
        result = cursor.fetchone()
        return result[0] if result else 0

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
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT local_path FROM images WHERE url = ?', (url,))
        result = cursor.fetchone()
        if result:
            return os.path.basename(result[0])

        image_uuid = str(uuid.uuid4())
        filename = f"{image_uuid}.jpg"
        local_path = os.path.join(self.pic_dir, filename)

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            if download_image(url, local_path):
                cursor.execute('INSERT INTO images (url, local_path) VALUES (?, ?)', (url, local_path))
                conn.commit()
                return image_uuid
        except Exception as e:
            print(f"An error occurred while downloading image: {e}")
        
        return None

    def get_image_base64(self, local_path):
        full_path = os.path.join(self.pic_dir, local_path)
        if os.path.exists(full_path):
            with open(full_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        return None

    def close(self):
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
            del self.local.conn

    def search_words(self, group_id, keyword):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT question, answer FROM words WHERE group_id = ? AND (question LIKE ? OR answer LIKE ?)', 
                       (group_id, f'%{keyword}%', f'%{keyword}%'))
        return cursor.fetchall()

    def update_word(self, group_id, question, new_answer):
        conn = self.get_conn()
        cursor = conn.cursor()
        new_answer = self.process_image_cq(new_answer)
        cursor.execute('UPDATE words SET answer = ? WHERE group_id = ? AND question = ?', (new_answer, group_id, question))
        conn.commit()

    def get_admin_list(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT qq_number, level FROM admins ORDER BY level DESC')
        return cursor.fetchall()

    def remove_admin(self, qq_number):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM admins WHERE qq_number = ?', (str(qq_number),))
        conn.commit()
        # Update config file
        default_admins = get_default_admins(self.config)
        if str(qq_number) in default_admins:
            default_admins.remove(str(qq_number))
            self.config.set("WordManagement", "default_admins", ",".join(default_admins))
            save_config(self.config, self.plugin_dir)

    def clean_unused_images(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT local_path FROM images')
        all_images = cursor.fetchall()
        
        for image_path in all_images:
            full_path = os.path.join(self.pic_dir, image_path[0])
            if not os.path.exists(full_path):
                cursor.execute('DELETE FROM images WHERE local_path = ?', (image_path[0],))
        
        conn.commit()

    def get_word_count(self, group_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM words WHERE group_id = ?', (group_id,))
        return cursor.fetchone()[0]

    def get_image_count(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM images')
        return cursor.fetchone()[0]

    def check_and_respond(self, group_id, message):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT answer FROM words WHERE group_id = ? AND question = ?', (group_id, message))
        result = cursor.fetchone()

        if not result:
            return None

        answer = result[0]
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

        answer = re.sub(img_pattern, replace_image, answer)
        return answer

    def regex_search(self, group_id, pattern):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT question, answer FROM words WHERE group_id = ?', (group_id,))
        all_words = cursor.fetchall()
        matches = []
        for question, answer in all_words:
            if re.search(pattern, question) or re.search(pattern, answer):
                matches.append((question, answer))
        return matches

    def is_super_admin(self, qq_number):
        return str(qq_number) == get_super_admin(self.config)

    def get_questions(self, group_id, question_id=None):
        conn = self.get_conn()
        cursor = conn.cursor()
        if question_id == 'all':
            cursor.execute('SELECT id, question FROM words WHERE group_id = ? ORDER BY id', (group_id,))
        elif question_id:
            cursor.execute('SELECT id, question FROM words WHERE group_id = ? AND id = ?', (group_id, question_id))
        else:
            return []
        return cursor.fetchall()