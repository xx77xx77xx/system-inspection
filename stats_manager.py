import json
import os
from datetime import datetime

STATS_FILE = "data/stats.json"

def load_stats():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(STATS_FILE):
        return {"consecutive_days": 0, "last_check_date": ""}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"consecutive_days": 0, "last_check_date": ""}

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)

def update_consecutive_days(all_ok):
    """
    更新连续正常运行天数。
    如果 all_ok 为 True，且日期变了，天数+1。
    如果 all_ok 为 False，天数归 0。
    """
    stats = load_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not all_ok:
        stats["consecutive_days"] = 0
        stats["last_check_date"] = today
    else:
        # 如果今天是新的成功日
        if stats["last_check_date"] != today:
            # 只有当之前也是 0 或者已经有成功记录时才累加
            # 实际上简单点：如果是 True 且日期变了就加 1
            stats["consecutive_days"] += 1
            stats["last_check_date"] = today
            
    save_stats(stats)
    return stats["consecutive_days"]

def get_consecutive_days():
    return load_stats().get("consecutive_days", 0)
