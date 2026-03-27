import subprocess
import platform
import socket


def ping_host(name, host, timeout=1000):
    """
    主机连通性检查（Ping）
    - Windows：ping -n 1 -w timeout
    - 无控制台弹窗（支持 pythonw）
    - timeout 单位：毫秒
    """
    try:
        system = platform.system().lower()

        if system == "windows":
            cmd = [
                "ping",
                "-n", "1",              # 只发 1 个包
                "-w", str(timeout),     # 超时时间（毫秒）
                host
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            # Linux / Unix
            cmd = ["ping", "-c", "1", "-W", "1", host]
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        ok = (result.returncode == 0)

        return {
            "type": "HOST",
            "name": name,
            "target": host,
            "ok": ok,
            "detail": "" if ok else "主机不可达"
        }

    except Exception as e:
        return {
            "type": "HOST",
            "name": name,
            "target": host,
            "ok": False,
            "detail": f"Ping异常：{e}"
        }


def check_tcp_port(name, host, port, timeout=3):
    """
    TCP 端口连通性检查（慢连接友好）
    - 不依赖 telnet / nc
    - socket 级别，不弹窗
    - timeout 单位：秒
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, int(port)))

        return {
            "type": "TCP",
            "name": name,
            "target": f"{host}:{port}",
            "ok": True,
            "detail": ""
        }

    except socket.timeout:
        return {
            "type": "TCP",
            "name": name,
            "target": f"{host}:{port}",
            "ok": False,
            "detail": "连接超时"
        }

    except Exception as e:
        return {
            "type": "TCP",
            "name": name,
            "target": f"{host}:{port}",
            "ok": False,
            "detail": f"连接失败：{e}"
        }

    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def check_telnet(name, host, port, timeout=3):
    """
    Telnet 方式检查（本质为 TCP 握手，增加业务语义）
    - 兼容现有 TCP 逻辑
    - 返回类型设为 TELNET
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, int(port)))

        return {
            "type": "TELNET",
            "name": name,
            "target": f"{host}:{port}",
            "ok": True,
            "detail": ""
        }

    except socket.timeout:
        return {
            "type": "TELNET",
            "name": name,
            "target": f"{host}:{port}",
            "ok": False,
            "detail": "Telnet连接超时"
        }

    except Exception as e:
        return {
            "type": "TELNET",
            "name": name,
            "target": f"{host}:{port}",
            "ok": False,
            "detail": f"Telnet连接异常：{e}"
        }

    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass
