import requests
import json
from datetime import datetime
from config_manager import load_config
from stats_manager import get_consecutive_days
from logger import logger


def get_weekday_str():
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return weekdays[datetime.now().weekday()]


def send_alert(msg_body):
    """
    发送企微机器人消息（text类型，严格按官方文档格式）。
    官方文档: https://developer.work.weixin.qq.com/document/path/99110
    返回: (success: bool, detail: str)
    """
    config = load_config().get("ALERT_CONFIG", {})
    alert_url = config.get("url", "")
    alert_key = config.get("key", "")

    if not alert_url:
        logger.warning("未配置企微 webhook，跳过发送。")
        return False, "未配置 Webhook URL"

    # 构造完整 Webhook 地址
    full_url = alert_url
    if alert_key and "key=" not in full_url:
        separator = "&" if "?" in full_url else "?"
        full_url = "{}{}key={}".format(full_url, separator, alert_key)

    # 严格按照官方文档格式构造 payload
    payload = {
        "msgtype": "text",
        "text": {
            "content": msg_body
        }
    }

    # 手动序列化 JSON，确保 UTF-8 编码
    json_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            full_url,
            data=json_data,
            headers=headers,
            timeout=10
        )
        resp_text = response.text
        logger.info("Webhook响应 [{}]: {}".format(response.status_code, resp_text[:500]))

        if response.status_code == 200:
            try:
                resp_json = response.json()
                errcode = resp_json.get("errcode", resp_json.get("code", -1))
                errmsg = resp_json.get("errmsg", resp_json.get("msg", ""))
                if errcode != 0:
                    logger.error("企微返回错误: errcode={}, errmsg={}".format(errcode, errmsg))
                    return False, "errcode={}, errmsg={}".format(errcode, errmsg)
            except (ValueError, AttributeError):
                pass
            return True, "OK (resp: {})".format(resp_text[:200])
        else:
            logger.error("HTTP错误 [{}]: {}".format(response.status_code, resp_text))
            return False, "HTTP {}: {}".format(response.status_code, resp_text[:200])

    except requests.exceptions.Timeout:
        logger.error("请求超时: {}".format(full_url))
        return False, "请求超时"
    except requests.exceptions.ConnectionError as e:
        logger.error("连接失败: {}".format(e))
        return False, "连接失败: {}".format(e)
    except Exception as e:
        logger.error("发送异常: {}".format(e))
        return False, "异常: {}".format(e)


def build_msg(title, detail):
    """构建单条故障/恢复告警消息"""
    now = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    weekday = get_weekday_str()
    
    return (
        "\U0001F4CB 信息科系统巡检报告\n"
        "\U0001F552 时间: {} {} {}\n"
        "\U0001F4CB 项目: {}\n"
        "\U0001F4DD 详情: {}\n"
    ).format(now, weekday, time_str, title, detail)


def send_daily_report(results):
    """
    发送巡检汇总通知。
    - 简洁播报: 总数 / 正常 / 异常 / 慢连接
    - 异常时: 列出具体服务名称和地址
    - 全部正常时: 显示鼓励语 + 连续正常天数
    返回: (success: bool, detail: str)
    """
    if not results:
        return False, "无巡检结果"

    now_date = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")
    weekday = get_weekday_str()

    ok_list = []
    fail_list = []
    slow_list = []
    for r in results:
        if not r.get("ok"):
            fail_list.append(r)
        else:
            ok_list.append(r)
            if r.get("slow"):
                slow_list.append(r)

    total = len(results)
    ok_count = len(ok_list)
    fail_count = len(fail_list)
    slow_count = len(slow_list)
    
    days = get_consecutive_days()

    # 构建美化消息
    lines = [
        "\U0001F4CB 信息科系统巡检报告",
        "\U0001F552 时间: {} {} {}".format(now_date, weekday, now_time),
        "\U0001F3DF️ 连续正常运行: {} 天".format(days),
        "",
        "\U0001F4E6 巡检总数: {} 项".format(total),
        "\u2705 正常运行: {} 项".format(ok_count),
        "\u274C 异常故障: {} 项".format(fail_count),
        "\u26A0\uFE0F  慢连接:  {} 项".format(slow_count),
    ]

    # 异常详情
    if fail_list:
        lines.append("")
        lines.append("\U0001F534 异常服务明细:")
        for i, r in enumerate(fail_list, 1):
            name = r.get("name", "未知")
            target = r.get("target", "")
            detail = r.get("detail", "")
            lines.append("  {}. {} ".format(i, name))
            lines.append("     地址: {}".format(target))
            if detail:
                lines.append("     原因: {}".format(detail))

    # 慢连接详情
    if slow_list:
        lines.append("")
        lines.append("\U0001F7E1 慢连接明细:")
        for i, r in enumerate(slow_list, 1):
            name = r.get("name", "未知")
            detail = r.get("detail", "")
            lines.append("  {}. {} - {}".format(i, name, detail))

    # 全部正常
    if not fail_list and not slow_list:
        lines.append("")
        lines.append("\U0001F389 所有服务运行正常，系统状态良好!")

    lines.append("")
    lines.append("\U0001F916 信息科系统巡检机器人")

    msg_body = "\n".join(lines)
    return send_alert(msg_body)
