
import os
import configparser

BLACK_GROUPS = [965482191]

def config_init(dir):
    config_file_name = 'dict_config.ini'
    config_path = os.path.join(dir, config_file_name)
    config = configparser.ConfigParser()

    if not os.path.exists(config_path):
        config['WordManagement'] = {
            "default_admins": "851845341,123456789",  # 替换为实际的默认管理员QQ号
            "super_admin": "851845341"  # 替换为实际的超级管理员QQ号
        }
        with open(config_path, 'w') as configfile:
            config.write(configfile)
    else:
        config.read(config_path)

    return config

def get_default_admins(config):
    default_admins = config.get("WordManagement", "default_admins", fallback="").split(",")
    return [admin.strip() for admin in default_admins if admin.strip()]

def get_super_admin(config):
    return config.get("WordManagement", "super_admin", fallback="")

def save_config(config, dir):
    config_file_name = 'dict_config.ini'
    config_path = os.path.join(dir, config_file_name)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
