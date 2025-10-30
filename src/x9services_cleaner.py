# X9 Cleaner — discord.gg/x9services
# (c) 2025 X9 Services. MIT License (Attribution Required).

import os
import sys
import shutil
import subprocess
import time
import ctypes
from datetime import datetime
from PyQt6 import QtWidgets, QtGui, QtCore
import urllib.request
import tempfile

# Privilege Handling
def ensure_admin():
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            sys.exit(0)
    except Exception:
        pass


# Utility
def safe_expand(path):
    return os.path.expandvars(path) if path else path


def delete_path(path, log, color):
    path = safe_expand(path)
    if not path:
        return
    if not os.path.exists(path):
        log(f"Not found: {path}", "orange")
        return
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            log(f"Deleted folder: {path}", color)
        elif os.path.isfile(path):
            os.remove(path)
            log(f"Deleted file: {path}", color)
    except Exception as e:
        log(f"Error deleting {path}: {e}", "red")


# Cleaning Tasks
def clean_fivem(log):
    """Clean FiveM.app directories thoroughly."""
    local = os.getenv("LOCALAPPDATA") or ""
    base_path = os.path.join(local, "FiveM", "FiveM.app")

    if not os.path.exists(base_path):
        log("FiveM.app folder not found.", "orange")
        return

    log("Cleaning FiveM.app and related data...", "cyan")

    # Target directories
    targets = [
        os.path.join(base_path, "citizen"),
        os.path.join(base_path, "data", "cache"),
        os.path.join(base_path, "data", "nui-storage"),
        os.path.join(base_path, "data", "server-cache"),
        os.path.join(base_path, "data", "server-cache-priv"),
    ]

    # External traces
    external_targets = [
        os.path.join(os.getenv("APPDATA", ""), "CitizenFX"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "D3DSCache"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "DigitalEntitlements"),
    ]

    deleted_count = 0
    for path in targets + external_targets:
        if os.path.exists(path):
            delete_path(path, log, "lightgreen")
            deleted_count += 1
        else:
            log(f"Skipped (not found): {path}", "orange")

    if deleted_count == 0:
        log("No FiveM data found to delete.", "orange")
    else:
        log(f"FiveM cleaning complete. {deleted_count} items removed.", "green")

def unlink_rockstar(log):
    """
    Delete DigitalEntitlements to unlink Rockstar accounts.
    Safe delete: logs if missing and reports success.
    """
    path = os.path.join(os.getenv("LOCALAPPDATA", ""), "DigitalEntitlements")
    log("Unlinking Rockstar: removing DigitalEntitlements...", "cyan")
    if os.path.exists(path):
        delete_path(path, log, "lightgreen")
        log("Unlink Rockstar complete.", "green")
    else:
        log(f"DigitalEntitlements not found: {path}", "orange")

def clean_temp(log):
    local = os.getenv("LOCALAPPDATA") or ""
    windir = os.getenv("WINDIR") or ""
    paths = [
        os.path.join(local, "Temp"),
        os.path.join(local, "CrashDumps"),
        os.path.join(windir, "Temp"),
        os.path.join(windir, "Prefetch"),
    ]
    log("Cleaning temporary and prefetch data...", "cyan")
    for p in paths:
        delete_path(p, log, "lightgreen")
    log("Temp file cleaning complete.", "green")


def clean_microsoft(log):
    path = os.path.join(os.getenv("PROGRAMDATA", ""), "Microsoft", "Windows", "WER", "ReportArchive")
    log("Cleaning Microsoft error logs...", "cyan")
    delete_path(path, log, "lightgreen")
    log("Microsoft logs cleaned.", "green")


def clean_steam(log):
    local = os.getenv("LOCALAPPDATA") or ""
    path = os.path.join(local, "Steam", "htmlcache")
    log("Cleaning Steam cache...", "cyan")
    delete_path(path, log, "lightgreen")
    log("Steam cleaning complete.", "green")


def kill_processes(log):
    processes = [
        "steam.exe",
        "steamwebhelper.exe",
        "steamservice.exe",
        "FiveM.exe",
        "FiveM_Diag.exe",
        "FiveM_ChromeBrowser.exe",
    ]
    log("Terminating running game processes...", "cyan")

    for proc in processes:
        try:
            result = subprocess.run(
                f'tasklist | find /i "{proc}"',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if proc.lower() in result.stdout.lower():
                try:
                    subprocess.run(
                        f"taskkill /f /im {proc}",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    log(f"Terminated: {proc}", "lightgreen")
                except FileNotFoundError:
                    log(f"Skipped missing runtime file for {proc}", "orange")
                except Exception as e:
                    log(f"Error terminating {proc}: {e}", "red")
            else:
                log(f"Not running: {proc}", "orange")

        except Exception as e:
            log(f"Process check failed for {proc}: {e}", "red")

    log("Process termination complete.", "green")


# Worker Thread
class Worker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str, str)
    progress_signal = QtCore.pyqtSignal(int, str)
    finished_signal = QtCore.pyqtSignal()

    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks

    def log(self, text, color="white"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"[{ts}] {text}", color)

    def run(self):
        total = len(self.tasks)
        for i, task in enumerate(self.tasks):
            self.progress_signal.emit(int((i / total) * 100), f"Running {task}...")
            try:
                if task == "clean_fivem":
                    clean_fivem(self.log)
                elif task == "clean_temp":
                    clean_temp(self.log)
                elif task == "clean_microsoft":
                    clean_microsoft(self.log)
                elif task == "clean_steam":
                    clean_steam(self.log)
                elif task == "kill_processes":
                    kill_processes(self.log)
                elif task == "unlink_rockstar":
                    unlink_rockstar(self.log)
            except Exception as e:
                self.log(f"Task {task} failed: {e}", "red")
            self.progress_signal.emit(int(((i + 1) / total) * 100), f"Completed {task}")
            time.sleep(0.25)
        self.log("All tasks finished.", "cyan")
        self.finished_signal.emit()


# Main GUI
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("X9 Cleaner — discord.gg/x9services")
        self.setMinimumSize(960, 540)
        self.worker = None

        icon_path = os.path.join(tempfile.gettempdir(), "x9_icon.png")
        try:
            urllib.request.urlretrieve(
                "https://r2.fivemanage.com/pBiGGCmRzm0Awt8Uc72Pb/image_2025-10-26_232314568.png", icon_path
            )
            self.setWindowIcon(QtGui.QIcon(icon_path))
        except Exception:
            pass

        self.build_ui()

    def build_ui(self):
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background-color: #0a0a0a; border-right: 1px solid #111;")
        sbox = QtWidgets.QVBoxLayout(sidebar)
        sbox.setContentsMargins(15, 20, 15, 20)
        sbox.setSpacing(10)

        title = QtWidgets.QLabel("X9 Cleaner")
        title.setStyleSheet("color: #45a9ff; font-size: 22px; font-weight: bold;")
        sbox.addWidget(title)

        subtitle = QtWidgets.QLabel("discord.gg/x9services")
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        sbox.addWidget(subtitle)
        sbox.addSpacing(20)

        actions = [
            ("Unlink Rockstar Account", ["unlink_rockstar"]),
            ("Clean FiveM Files", ["clean_fivem"]),
            ("Clean Temp Files", ["clean_temp"]),
            ("Clean Steam", ["clean_steam"]),
            ("Clean Microsoft Logs", ["clean_microsoft"]),
            ("Kill Game Processes", ["kill_processes"]),
            ("Full Clean (All)", ["kill_processes", "clean_fivem", "clean_temp", "clean_microsoft", "clean_steam"]),
        ]

        for label, tasks in actions:
            btn = QtWidgets.QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #111;
                    color: #45a9ff;
                    border: 1px solid #222;
                    padding: 10px;
                    border-radius: 6px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #1a1a1a;
                    border: 1px solid #45a9ff;
                }
            """)
            btn.clicked.connect(lambda _, t=tasks: self.start_tasks(t))
            sbox.addWidget(btn)

        sbox.addStretch(1)
        layout.addWidget(sidebar)

        main = QtWidgets.QFrame()
        main.setStyleSheet("background-color: #050505;")
        mbox = QtWidgets.QVBoxLayout(main)
        mbox.setContentsMargins(15, 15, 15, 15)

        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            QTextEdit {
                background-color: #000;
                color: #e0f0ff;
                font-family: Consolas;
                border: 1px solid #222;
                border-radius: 6px;
            }
        """)
        mbox.addWidget(self.log_view, 1)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Idle")
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                height: 6px;
                background-color: #111;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #45a9ff;
                border-radius: 3px;
            }
        """)
        mbox.addWidget(self.progress)
        layout.addWidget(main, 1)

    def append_log(self, text, color):
        self.log_view.append(f'<span style="color:{color}">{text}</span>')
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def start_tasks(self, tasks):
        if self.worker and self.worker.isRunning():
            return
        self.log_view.clear()
        self.progress.setValue(0)
        self.worker = Worker(tasks)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(lambda: self.progress.setFormat("Done"))
        self.worker.start()

    def update_progress(self, val, text):
        self.progress.setValue(val)
        self.progress.setFormat(text)


# Entrypoint
def main():
    ensure_admin()
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
