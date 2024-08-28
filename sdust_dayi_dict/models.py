# models.py
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Word(Base):
    __tablename__ = 'words'
    id = Column(Integer, primary_key=True)
    group_id = Column(String)
    question = Column(Text)
    answer = Column(Text)

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    qq_number = Column(String)
    level = Column(Integer)

class Image(Base):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True)
    url = Column(String)
    local_path = Column(String)

class Alias(Base):
    __tablename__ = 'aliases'
    id = Column(Integer, primary_key=True)
    group_id = Column(String)
    alias = Column(String)
    command = Column(Text)

def init_db(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)