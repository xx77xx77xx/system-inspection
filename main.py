import time
from colorama import Fore, Style, init

from inspect_url import check_url
from inspect_db import check_oracle, check_mysql
from inspect_host import ping_host, check_tcp_port, check_telnet
from alert import send_alert, build_msg
from config_manager import load_config
from logger import log_result
from executor import run_parallel
from stats_manager import update_consecutive_days

# 初始化 colorama（Windows 必须）
init(autoreset=True)

# =========================
# 内存态状态
# =========================
LAST_STATUS = {}      # key -> True / False
FAIL_COUNT = {}       # key -> 连续失败次数
FAIL_THRESHOLD = 3    # 连续失败阈值（防抖）
ALERT_COUNT = {}      # key -> 已发送告警次数
MAX_ALERT_PER_FAULT = 5   # 单个故障最多告警次数

# =========================
# 重试机制配置
# =========================
RETRY_TIMES = 2       # 失败后自动重试次数
RETRY_INTERVAL = 1    # 重试间隔秒


# =========================
# 控制台彩色输出
# =========================
def print_console(result):
    try:
        ok = result.get("ok", False)
        slow = result.get("slow", False)

        if not ok:
            color = Fore.RED
            status = "异常"
        elif slow:
            color = Fore.YELLOW
            status = "慢"
        else:
            color = Fore.GREEN
            status = "正常"

        print(
            color +
            f"[{result['type']}] "
            f"{result['name']} -> {status} | "
            f"{result['target']} | "
            f"{result.get('detail', '')}"
            + Style.RESET_ALL
        )
    except Exception:
        # 如果控制台输出失败（如 Win7 下的设备写入错误），保持静默以确保流程不中断
        pass



# =========================
# 统一结果处理
# =========================
def handle_result(result):
    """
    统一处理巡检结果
    - 连续失败 N 次才告警（防抖）
    - 单个故障最多告警 MAX_ALERT_PER_FAULT 次
    - 恢复只告警一次，并重置计数器
    - 慢连接单独告警
    """
    log_result(result)
    print_console(result)

    key = f"{result['type']}|{result['target']}"
    last_ok = LAST_STATUS.get(key)
    fail_times = FAIL_COUNT.get(key, 0)
    alerted = ALERT_COUNT.get(key, 0)

    # ---------- 当前异常 ----------
    if not result.get("ok", False):
        fail_times += 1
        FAIL_COUNT[key] = fail_times
        LAST_STATUS[key] = False

        # 达到防抖阈值 且 未超过最大告警次数
        if fail_times >= FAIL_THRESHOLD and alerted < MAX_ALERT_PER_FAULT:
            ALERT_COUNT[key] = alerted + 1
            msg = build_msg(
                result["name"],
                f"目标：{result['target']}\n"
                f"原因：{result['detail']}\n"
                f"连续失败：{fail_times} 次\n"
                f"告警次数：{alerted + 1}/{MAX_ALERT_PER_FAULT}"
            )
            send_alert(msg)
        return

    # ---------- 当前正常 ----------
    FAIL_COUNT[key] = 0

    # 从异常恢复 → 通知 + 重置告警计数
    if last_ok is False:
        ALERT_COUNT[key] = 0
        msg = build_msg(
            f"{result['name']} 已恢复",
            f"目标：{result['target']}\n状态：恢复正常"
        )
        send_alert(msg)

    # ---------- 慢连接告警 ----------
    if result.get("slow"):
        msg = build_msg(
            f"{result['name']} 慢连接告警",
            f"目标：{result['target']}\n详情：{result['detail']}"
        )
        send_alert(msg)

    LAST_STATUS[key] = True


# =========================
# 任务重试包装
# =========================
def run_with_retry(task):
    """
    执行任务，如果失败会自动重试 RETRY_TIMES 次
    返回最终结果（最后一次执行结果）
    """
    for attempt in range(1, RETRY_TIMES + 2):  # +1 是第一次尝试
        result = task()
        if result.get("ok", False):
            return result
        if attempt <= RETRY_TIMES:
            time.sleep(RETRY_INTERVAL)
    return result


# =========================
# 构建巡检任务
# =========================
def build_tasks():
    tasks = []
    cfg = load_config()

    # URL 检查
    for item in cfg.get("URL_CHECKS", []):
        tasks.append(lambda n=item.get("name"), u=item.get("url"), m=item.get("method", "GET"): check_url(n, u, m))

    # Oracle 检查
    for db in cfg.get("ORACLE_DBS", []):
        tasks.append(lambda db=db: check_oracle(
            name=db.get("name"),
            user=db.get("user"),
            password=db.get("password"),
            host=db.get("host"),
            port=db.get("port"),
            service=db.get("service"),
            timeout=int(db.get("timeout", 5)),
            conn_threshold=3,
            sql_threshold=1,
            total_threshold=4
        ))

    # MySQL 检查
    for db in cfg.get("MYSQL_DBS", []):
        tasks.append(lambda db=db: check_mysql(
            name=db.get("name"),
            user=db.get("user"),
            password=db.get("password"),
            host=db.get("host"),
            port=db.get("port"),
            database=db.get("database"),
            timeout=int(db.get("timeout", 5)),
            conn_threshold=3,
            sql_threshold=1,
            total_threshold=4
        ))

    # 主机 ping
    for item in cfg.get("HOSTS", []):
        tasks.append(lambda n=item.get("name"), h=item.get("host"): ping_host(n, h))

    # TCP 端口
    for item in cfg.get("TCP_PORTS", []):
        tasks.append(lambda i=item: check_tcp_port(
            i.get("name"),
            i.get("host"),
            i.get("port")
        ))

    # Telnet 方式
    for item in cfg.get("TELNET_CHECKS", []):
        tasks.append(lambda i=item: check_telnet(
            i.get("name"),
            i.get("host"),
            i.get("port"),
            timeout=i.get("timeout", 3)
        ))

    return tasks


# =========================
# 执行巡检并收集结果（供每日报告使用）
# =========================
def run_and_collect():
    """执行巡检并返回结果列表，不触发实时告警"""
    tasks = build_tasks()
    retry_tasks = [lambda t=task: run_with_retry(t) for task in tasks]
    results = run_parallel(retry_tasks)

    # 记录日志、控制台输出并检查是否全量通过
    all_ok = True
    for r in results:
        log_result(r)
        print_console(r)
        if not r.get("ok", False):
            all_ok = False
            
    update_consecutive_days(all_ok)


    return results


# =========================
# 主执行逻辑
# =========================
def main():
    print(Fore.CYAN + "\n===== 医院系统巡检开始 =====\n" + Style.RESET_ALL)

    tasks = build_tasks()

    # 并发执行任务，包装重试机制
    retry_tasks = [lambda t=task: run_with_retry(t) for task in tasks]
    results = run_parallel(retry_tasks)

    # 统一处理结果（含实时故障告警）
    all_ok = True
    for r in results:
        handle_result(r)
        if not r.get("ok", False):
            all_ok = False

    # 更新连续正常天数统计
    update_consecutive_days(all_ok)

    # 耗时排行
    print(Fore.CYAN + "\n===== 巡检耗时排行 =====" + Style.RESET_ALL)
    cost_list = [r for r in results if "total_cost" in r]
    for r in sorted(cost_list, key=lambda x: x.get("total_cost", 0), reverse=True):
        print(f"{r['name']:<20} {r['total_cost']}s")

    print(Fore.CYAN + "\n===== 巡检结束 =====\n" + Style.RESET_ALL)


if __name__ == "__main__":
    main()