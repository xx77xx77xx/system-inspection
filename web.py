import hashlib
import secrets
from fastapi import FastAPI, BackgroundTasks, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
import csv
import io
from starlette.middleware.base import BaseHTTPMiddleware
from collections import deque
import json
import os
import threading
import time
from json import JSONDecodeError

from config_manager import load_config, save_config
from alert import send_daily_report
from logger import logger
import main as inspector

app = FastAPI()

LOG_FILE = "logs/inspection.log"

# =========================
# 登录鉴权
# =========================
ADMIN_USER = "admin"
ADMIN_PASS = "890622"  # 明文密码
SESSION_TOKENS = set()  # 内存中存储有效的 session token

# 白名单路径（无需登录即可访问）
AUTH_WHITELIST = ["/login", "/api/login"]


class AuthMiddleware(BaseHTTPMiddleware):
    """Cookie 会话鉴权中间件"""
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 白名单路径放行
        for wp in AUTH_WHITELIST:
            if path.startswith(wp):
                return await call_next(request)

        # 检查 cookie 中的 session token
        token = request.cookies.get("session_token", "")
        if token and token in SESSION_TOKENS:
            return await call_next(request)

        # 未登录：API 请求返回 401，页面请求重定向到登录页
        if path.startswith("/api/"):
            return JSONResponse({"code": 401, "msg": "未登录"}, status_code=401)

        return RedirectResponse(url="/login", status_code=302)


app.add_middleware(AuthMiddleware)


# =========================
# 登录相关路由
# =========================
@app.get("/login")
def login_page():
    return FileResponse("login.html")


@app.post("/api/login")
async def do_login(request: Request):
    try:
        data = await request.json()
        username = data.get("username", "")
        password = data.get("password", "")

        if username == ADMIN_USER and password == ADMIN_PASS:
            token = secrets.token_hex(16)
            SESSION_TOKENS.add(token)
            response = JSONResponse({"code": 200, "msg": "登录成功"})
            response.set_cookie("session_token", token, httponly=True, max_age=86400)
            return response
        else:
            return JSONResponse({"code": 403, "msg": "用户名或密码错误"})
    except Exception as e:
        return JSONResponse({"code": 500, "msg": str(e)})


@app.get("/api/logout")
def do_logout(request: Request):
    token = request.cookies.get("session_token", "")
    SESSION_TOKENS.discard(token)
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response


# =========================
# API：配置管理 CRUD
# =========================
@app.get("/api/config")
def get_system_config():
    """获取当前的系统巡检配置文件"""
    return load_config()

@app.post("/api/config")
async def update_system_config(request: Request):
    """保存前端提交的新配置"""
    try:
        data = await request.json()
        save_config(data)
        return {"code": 200, "msg": "配置保存成功"}
    except Exception as e:
        return {"code": 500, "error": str(e)}

# =========================
# API：手动触发与后台调度
# =========================
is_inspecting = False

def run_inspection_job():
    global is_inspecting
    is_inspecting = True
    try:
        inspector.main()
    except Exception as e:
        logger.error(f"后台巡检执行异常: {e}")
    finally:
        is_inspecting = False

@app.post("/api/inspect/trigger")
async def trigger_inspection(background_tasks: BackgroundTasks):
    """手动立即触发全量巡检"""
    global is_inspecting
    if is_inspecting:
        return {"code": 400, "msg": "当前已有巡检任务正在执行中..."}
    
    background_tasks.add_task(run_inspection_job)
    return {"code": 200, "msg": "巡检指令已发送至后台队列！"}

@app.post("/api/alert/test")
async def test_alert():
    """
    分两步测试:
    1. 先发一条极简消息验证 webhook 是否连通
    2. 再执行巡检并发送报告
    """
    from alert import send_alert as _send
    try:
        # 步骤1: 发送极简测试消息
        test_msg = "巡检系统连通测试 - {}".format(
            datetime.now().strftime("%H:%M:%S")
        )
        ok1, detail1 = _send(test_msg)
        if not ok1:
            return {"code": 500, "msg": "连通测试失败: {}".format(detail1)}

        # 步骤2: 执行巡检并发送报告
        results = inspector.run_and_collect()
        if not results:
            return {"code": 200, "msg": "连通测试成功! 但未配置巡检项目。响应: {}".format(detail1)}

        ok2, detail2 = send_daily_report(results)
        if ok2:
            return {"code": 200, "msg": "发送成功! 共{}项。响应: {}".format(len(results), detail2)}
        else:
            return {"code": 500, "msg": "连通测试OK, 但报告发送失败: {}".format(detail2)}

    except Exception as e:
        logger.error("测试告警异常: {}".format(e))
        return {"code": 500, "msg": "执行异常: {}".format(str(e))}




from datetime import datetime, timedelta

# 后台自动定时巡检调度器
@app.on_event("startup")
def startup_event():
    def auto_run_job():
        time.sleep(10)
        while True:
            time.sleep(300)
            if not is_inspecting:
                run_inspection_job()

    def daily_report_job():
        """每天早上 9:00 发送巡检日报"""
        while True:
            now = datetime.now()
            target = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            logger.info(f"[日报调度] 下次发送时间: {target.strftime('%Y-%m-%d %H:%M:%S')}，等待 {int(wait_seconds)} 秒")
            time.sleep(wait_seconds)

            try:
                logger.info("[日报调度] 正在执行巡检并生成日报...")
                results = inspector.run_and_collect()
                send_daily_report(results)
                logger.info("[日报调度] 日报发送完成")
            except Exception as e:
                logger.error(f"[日报调度] 日报发送异常: {e}")

    t1 = threading.Thread(target=auto_run_job, daemon=True)
    t1.start()

    t2 = threading.Thread(target=daily_report_job, daemon=True)
    t2.start()


# =========================
# API：批量导入与模板
# =========================
@app.get("/api/import/template")
def download_template():
    """下载 CSV 导入模板"""
    template_path = "import_template.csv"
    if os.path.exists(template_path):
        return FileResponse(template_path, filename="import_template.csv", media_type="text/csv")
    return JSONResponse({"code": 404, "msg": "模板文件未找到"}, status_code=404)

@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...)):
    """解析上传的 CSV 并返回 JSON 列表"""
    try:
        content = await file.read()
        text = content.decode("utf-8-sig")  # 处理可能包含 BOM 的 UTF-8
        f = io.StringIO(text)
        reader = csv.DictReader(f)
        
        results = []
        for row in reader:
            name = row.get("name", "").strip()
            host = row.get("host", "").strip()
            if name and host:
                results.append({"name": name, "host": host})
        
        return {"code": 200, "data": results, "msg": f"成功读取 {len(results)} 条数据"}
    except Exception as e:
        logger.error(f"解析 CSV 异常: {e}")
        return JSONResponse({"code": 500, "msg": f"解析失败: {str(e)}"}, status_code=500)

# =========================
# API：获取巡检状态日志
# =========================
@app.get("/status")
def get_status():
    try:
        if not os.path.exists(LOG_FILE):
            return {"data": []}

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = deque(f, maxlen=100)

        data = []
        for line in lines:
            raw = line.strip()
            if not raw:
                continue
            try:
                data.append(json.loads(raw))
            except JSONDecodeError:
                continue

        return {"data": data}

    except Exception as e:
        return {"error": str(e)}

# =========================
# 提供 dashboard 页面
# =========================
@app.get("/")
def dashboard():
    return FileResponse("dashboard.html")

# =========================
# 静态文件支持
# =========================
app.mount("/static", StaticFiles(directory="."), name="static")
