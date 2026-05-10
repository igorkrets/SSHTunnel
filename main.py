import sys
import os
import json
import base64
import subprocess
import threading
from PyQt5 import QtWidgets, QtGui, QtCore
from cryptography.fernet import Fernet
import paramiko

APP_NAME = "SSHTunnelManager"
ICON_PATH = os.path.join(os.path.dirname(__file__), "tray_icon.ico")
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
            transport.request_port_forward(
                '',
                int(self.conn['forward_port']),
                '127.0.0.1',
                int(self.conn['local_port'])
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
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))
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
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))
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
        super().__init__(QtGui.QIcon(ICON_PATH), app)
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
