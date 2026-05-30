"""Daily Planner server launcher.

Usage:
    python run.py              Start server normally
    python run.py --install    Install as Windows startup task
    python run.py --uninstall  Remove Windows startup task
"""
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
BAT_NAME = "DailyPlanner.bat"


def _startup_dir():
    return os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def _bat_path():
    return os.path.join(_startup_dir(), BAT_NAME)


def install_startup():
    """Create a .bat file in the Windows Startup folder."""
    bat_content = f'''@echo off
cd /d "{PROJECT_DIR}"
start /min "" "{PYTHON}" "{__file__}"
'''
    os.makedirs(_startup_dir(), exist_ok=True)
    with open(_bat_path(), "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"已安装开机自启动: {_bat_path()}")
    print("下次登录时服务器将自动启动。")


def uninstall_startup():
    """Remove the startup .bat file."""
    p = _bat_path()
    if os.path.exists(p):
        os.remove(p)
        print(f"已删除开机自启动: {p}")
    else:
        print("未找到开机自启动文件。")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--install":
            install_startup()
        elif sys.argv[1] == "--uninstall":
            uninstall_startup()
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法: python run.py [--install | --uninstall]")
    else:
        import uvicorn
        os.chdir(PROJECT_DIR)
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
