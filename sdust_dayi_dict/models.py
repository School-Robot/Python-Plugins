from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy import event
import sqlite3
import pymysql
from urllib.parse import urlparse
import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

Base = declarative_base()

class Word(Base):
    __tablename__ = 'words'
    id = Column(Integer, primary_key=True)
    group_id = Column(String(20))
    question = Column(Text)
    answer = Column(Text)

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    qq_number = Column(String(20), unique=True)
    level = Column(Integer)

class Image(Base):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True)
    url = Column(String(255))
    local_path = Column(String(255))

class Alias(Base):
    __tablename__ = 'aliases'
    id = Column(Integer, primary_key=True)
    group_id = Column(String(20))
    alias = Column(String(50))
    command = Column(Text)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def create_mysql_database_if_not_exists(url):
    parsed = urlparse(url)
    db_name = parsed.path.lstrip('/')
    db_url_without_name = f"{parsed.scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
    
    try:
        connection = pymysql.connect(
            host=parsed.hostname,
            user=parsed.username,
            password=parsed.password,
            port=parsed.port
        )
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"Database '{db_name}' created or already exists.")
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise
    finally:
        connection.close()

def init_db(database_url):
    try:
        if database_url.startswith('sqlite'):
            engine = create_engine(database_url)
        else:  # Assume MySQL
            # 尝试创建数据库（如果不存在）
            create_mysql_database_if_not_exists(database_url)
            
            # 添加 charset 参数以支持 utf8mb4
            if 'charset' not in database_url:
                database_url += '?charset=utf8mb4'
            engine = create_engine(database_url, pool_recycle=3600)

        # 尝试连接数据库
        connection = engine.connect()
        connection.close()

        Base.metadata.create_all(engine)
        logger.info("Database initialized successfully.")
        return sessionmaker(bind=engine)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def check_database_exists(database_url):
    try:
        engine = create_engine(database_url)
        connection = engine.connect()
        connection.close()
        logger.info("Database exists and is accessible.")
        return True
    except Exception as e:
        logger.error(f"Database does not exist or is not accessible: {e}")
        return False