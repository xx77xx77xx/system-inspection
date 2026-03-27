import json
import os

CONFIG_FILE = "data/config.json"

DEFAULT_CONFIG = {
    "URL_CHECKS": [],
    "ORACLE_DBS": [],
    "MYSQL_DBS": [],
    "HOSTS": [],
    "TCP_PORTS": [],
    "TELNET_CHECKS": [],
    "ALERT_CONFIG": {
        "url": "",
        "key": ""
    }
}

def load_config():
    """从本地 JSON 文件读取配置，如果不存在则初始化"""
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"配置文件读取失败: {e}")
        return DEFAULT_CONFIG

def save_config(config_data):
    """将修改后的配置覆写到本地 JSON 文件"""
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)
