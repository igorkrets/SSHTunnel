import sys
import os
import json
import base64
import tempfile
import atexit
import subprocess
import threading
from PyQt5 import QtWidgets, QtGui, QtCore
from cryptography.fernet import Fernet
import paramiko

APP_NAME = "SSHTunnelManager"
# tray_icon.ico вшит как base64
ICON_B64 = """
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
"""
def get_temp_icon_path():
    # Сохраняет иконку во временный файл и возвращает путь
    icon_bytes = base64.b64decode(ICON_B64)
    temp_dir = tempfile.gettempdir()
    icon_path = os.path.join(temp_dir, f"{APP_NAME}_tray_icon.ico")
    with open(icon_path, "wb") as f:
        f.write(icon_bytes)
    atexit.register(lambda: os.path.exists(icon_path) and os.remove(icon_path))
    return icon_path

TUNNEL_FILE = os.path.join(os.path.dirname(__file__), "tunnel.json")
KEY_FILE = os.path.join(os.path.dirname(__file__), "key.bin")

# --- Encryption helpers ---
def get_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
    else:
        with open(KEY_FILE, 'rb') as f:
            key = f.read()
    return key

def encrypt_password(password):
    key = get_key()
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()

def decrypt_password(token):
    key = get_key()
    f = Fernet(key)
    return f.decrypt(token.encode()).decode()

# --- SSH Tunnel Worker ---
class SSHTunnelWorker(QtCore.QThread):
    statusChanged = QtCore.pyqtSignal(str)

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.running = True
        self.ssh_client = None

    def run(self):
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.conn['host'],
                port=22,
                username=self.conn['user'],
                password=decrypt_password(self.conn['password'])
            )
            transport = self.ssh_client.get_transport()
            # Для reverse tunnel используем правильный вызов
            # (address, port, handler=None)
            transport.request_port_forward(
                '127.0.0.1',
                int(self.conn['forward_port'])
            )
            self.statusChanged.emit('Активно')
            while self.running:
                QtCore.QThread.msleep(1000)
        except Exception as e:
            self.statusChanged.emit(f'Ошибка: {e}')
        finally:
            if self.ssh_client:
                self.ssh_client.close()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# --- Main Window ---
class MainWindow(QtWidgets.QWidget):
    def __init__(self, tray_icon):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QtGui.QIcon(get_temp_icon_path()))
        self.tray_icon = tray_icon
        self.resize(600, 400)
        self.tunnels = []
        self.workers = {}
        self.init_ui()
        self.load_tunnels()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.add_btn = QtWidgets.QPushButton("[+] Добавить подключение")
        self.add_btn.clicked.connect(self.add_connection)
        layout.addWidget(self.add_btn)

        self.table = QtWidgets.QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Активно", "Host", "User", "Local Port", "Forward Port", "Статус", "Удалить"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.table)

    def load_tunnels(self):
        if os.path.exists(TUNNEL_FILE):
            with open(TUNNEL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.tunnels = data.get('connections', [])
        self.refresh_table()

    def save_tunnels(self):
        with open(TUNNEL_FILE, 'w', encoding='utf-8') as f:
            json.dump({'connections': self.tunnels}, f, ensure_ascii=False, indent=2)

    def refresh_table(self):
        self.table.setRowCount(0)
        for idx, conn in enumerate(self.tunnels):
            self.table.insertRow(idx)
            # Активно (тумблер)
            active_cb = QtWidgets.QCheckBox()
            active_cb.setChecked(conn.get('active', False))
            active_cb.stateChanged.connect(lambda state, i=idx: self.toggle_active(i, state))
            self.table.setCellWidget(idx, 0, active_cb)
            # Host
            self.table.setItem(idx, 1, QtWidgets.QTableWidgetItem(conn['host']))
            # User
            self.table.setItem(idx, 2, QtWidgets.QTableWidgetItem(conn['user']))
            # Local Port
            self.table.setItem(idx, 3, QtWidgets.QTableWidgetItem(str(conn['local_port'])))
            # Forward Port
            self.table.setItem(idx, 4, QtWidgets.QTableWidgetItem(str(conn['forward_port'])))
            # Status
            status_item = QtWidgets.QTableWidgetItem(conn.get('status', 'Неактивно'))
            self.table.setItem(idx, 5, status_item)
            # Delete
            del_btn = QtWidgets.QPushButton("Удалить")
            del_btn.clicked.connect(lambda _, i=idx: self.delete_connection(i))
            self.table.setCellWidget(idx, 6, del_btn)

    def add_connection(self):
        dlg = AddConnectionDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            conn = dlg.get_data()
            conn['active'] = True
            conn['status'] = 'Ожидание'
            self.tunnels.append(conn)
            self.save_tunnels()
            self.refresh_table()
            self.start_tunnel(len(self.tunnels)-1)

    def delete_connection(self, idx):
        self.stop_tunnel(idx)
        self.tunnels.pop(idx)
        self.save_tunnels()
        self.refresh_table()

    def toggle_active(self, idx, state):
        self.tunnels[idx]['active'] = bool(state)
        self.save_tunnels()
        if state:
            self.start_tunnel(idx)
        else:
            self.stop_tunnel(idx)
        self.refresh_table()

    def start_tunnel(self, idx):
        conn = self.tunnels[idx]
        if idx in self.workers:
            self.stop_tunnel(idx)
        worker = SSHTunnelWorker(conn)
        worker.statusChanged.connect(lambda status, i=idx: self.update_status(i, status))
        self.workers[idx] = worker
        worker.start()

    def stop_tunnel(self, idx):
        if idx in self.workers:
            self.workers[idx].stop()
            del self.workers[idx]
        self.tunnels[idx]['status'] = 'Неактивно'

    def update_status(self, idx, status):
        self.tunnels[idx]['status'] = status
        self.save_tunnels()
        self.refresh_table()

    def closeEvent(self, event):
        self.hide()
        event.ignore()
        self.tray_icon.showMessage(APP_NAME, "Приложение свернуто в трей.")

# --- Add Connection Dialog ---
class AddConnectionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Новое подключение")
        self.setWindowIcon(QtGui.QIcon(get_temp_icon_path()))
        layout = QtWidgets.QFormLayout(self)
        self.host = QtWidgets.QLineEdit()
        self.user = QtWidgets.QLineEdit()
        self.local_port = QtWidgets.QSpinBox()
        self.local_port.setRange(1, 65535)
        self.forward_port = QtWidgets.QSpinBox()
        self.forward_port.setRange(1, 65535)
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow("Host", self.host)
        layout.addRow("User", self.user)
        layout.addRow("Local Port", self.local_port)
        layout.addRow("Forward Port", self.forward_port)
        layout.addRow("Password", self.password)
        btns = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        self.buttonBox = QtWidgets.QDialogButtonBox(btns)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def get_data(self):
        return {
            'host': self.host.text(),
            'user': self.user.text(),
            'local_port': self.local_port.value(),
            'forward_port': self.forward_port.value(),
            'password': encrypt_password(self.password.text())
        }

# --- Tray Icon ---
class TrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, app, main_window):
        super().__init__(QtGui.QIcon(get_temp_icon_path()), app)
        self.app = app
        self.main_window = main_window
        self.setToolTip(APP_NAME)
        self.menu = QtWidgets.QMenu()
        self.settings_action = self.menu.addAction("Настройки")
        self.settings_action.triggered.connect(self.show_settings)
        self.disable_action = self.menu.addAction("Отключить автозагрузку")
        self.disable_action.triggered.connect(self.disable_autorun)
        self.exit_action = self.menu.addAction("Выход")
        self.exit_action.triggered.connect(self.exit_app)
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_activated)

    def show_settings(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def disable_autorun(self):
        remove_from_autorun()
        QtWidgets.QMessageBox.information(None, APP_NAME, "Автозагрузка отключена.")

    def exit_app(self):
        self.app.quit()

    def on_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.show_settings()

# --- Autorun ---
def add_to_autorun():
    import winreg
    exe = sys.executable
    script = os.path.abspath(__file__)
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}" "{script}"')
    winreg.CloseKey(key)

def remove_from_autorun():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except Exception:
        pass

# --- Main ---
def main():
    app = QtWidgets.QApplication(sys.argv)
    # Создать tunnel.json и key.bin если их нет
    if not os.path.exists(TUNNEL_FILE):
        with open(TUNNEL_FILE, 'w', encoding='utf-8') as f:
            json.dump({'connections': []}, f, ensure_ascii=False, indent=2)
    if not os.path.exists(KEY_FILE):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
    add_to_autorun()
    tray_icon = TrayIcon(app, None)
    main_window = MainWindow(tray_icon)
    tray_icon.main_window = main_window
    tray_icon.show()
    # Автозапуск активных туннелей
    for idx, conn in enumerate(main_window.tunnels):
        if conn.get('active', False):
            main_window.start_tunnel(idx)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
