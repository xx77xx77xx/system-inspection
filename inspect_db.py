import time
import oracledb
import mysql.connector


# =========================
# Oracle 巡检
# =========================
def check_oracle(
    name,
    user,
    password,
    host,
    port,
    service,
    timeout=5,
    conn_threshold=5,
    sql_threshold=10,
    total_threshold=15
):
    dsn = oracledb.makedsn(host, port, service_name=service)

    try:
        total_start = time.perf_counter()

        # ===== 1. 连接计时 =====
        conn_start = time.perf_counter()
        conn = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        conn_cost = round(time.perf_counter() - conn_start, 2)

        # ===== 2. SQL 计时 =====
        with conn.cursor() as cursor:
            sql_start = time.perf_counter()
            cursor.execute("SELECT 1 FROM dual")
            cursor.fetchone()
            sql_cost = round(time.perf_counter() - sql_start, 2)

        conn.close()

        total_cost = round(time.perf_counter() - total_start, 2)

        # ===== 慢分析 =====
        reasons = []
        if conn_cost >= conn_threshold:
            reasons.append("连接慢")
        if sql_cost >= sql_threshold:
            reasons.append("SQL慢")
        if total_cost >= total_threshold and not reasons:
            reasons.append("整体响应慢")

        slow = len(reasons) > 0

        detail = (
            f"Oracle 慢：{'/'.join(reasons)} | 连接 {conn_cost}s | SQL {sql_cost}s | 总计 {total_cost}s"
            if slow else
            f"Oracle 正常 | 连接 {conn_cost}s | SQL {sql_cost}s | 总计 {total_cost}s"
        )

        return {
            "type": "DB",
            "name": name,
            "target": dsn,
            "ok": True,
            "slow": slow,
            "conn_cost": conn_cost,
            "sql_cost": sql_cost,
            "total_cost": total_cost,
            "reason": reasons,
            "detail": detail
        }

    except Exception as e:
        return {
            "type": "DB",
            "name": name,
            "target": dsn,
            "ok": False,
            "slow": False,
            "detail": f"连接失败: {e}"
        }


# =========================
# MySQL 巡检
# =========================
def check_mysql(
    name,
    user,
    password,
    host,
    port,
    database,
    timeout=5,
    conn_threshold=5,
    sql_threshold=10,
    total_threshold=15
):
    target = f"{host}:{port}/{database}"

    try:
        total_start = time.perf_counter()

        # ===== 1. 连接计时 =====
        conn_start = time.perf_counter()
        conn = mysql.connector.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            connection_timeout=timeout
        )
        conn_cost = round(time.perf_counter() - conn_start, 2)

        # ===== 2. SQL 计时 =====
        cursor = conn.cursor()
        sql_start = time.perf_counter()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        sql_cost = round(time.perf_counter() - sql_start, 2)

        cursor.close()
        conn.close()

        total_cost = round(time.perf_counter() - total_start, 2)

        # ===== 慢分析 =====
        reasons = []
        if conn_cost >= conn_threshold:
            reasons.append("连接慢")
        if sql_cost >= sql_threshold:
            reasons.append("SQL慢")
        if total_cost >= total_threshold and not reasons:
            reasons.append("整体响应慢")

        slow = len(reasons) > 0

        detail = (
            f"MySQL 慢：{'/'.join(reasons)} | 连接 {conn_cost}s | SQL {sql_cost}s | 总计 {total_cost}s"
            if slow else
            f"MySQL 正常 | 连接 {conn_cost}s | SQL {sql_cost}s | 总计 {total_cost}s"
        )

        return {
            "type": "DB",
            "name": name,
            "target": target,
            "ok": True,
            "slow": slow,
            "conn_cost": conn_cost,
            "sql_cost": sql_cost,
            "total_cost": total_cost,
            "reason": reasons,
            "detail": detail
        }

    except Exception as e:
        return {
            "type": "DB",
            "name": name,
            "target": target,
            "ok": False,
            "slow": False,
            "detail": f"连接失败: {e}"
        }