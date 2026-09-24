from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFrame, QListWidget, QListWidgetItem, QVBoxLayout


class Sidebar(QFrame):
    newChatRequested = Signal()
    sessionSelected = Signal(str)
    sessionDeleteRequested = Signal(str)
    settingsRequested = Signal()
    sessionRenamed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        loader = QUiLoader()
        form = loader.load(str(Path(__file__).with_name("sidebar.ui")), self)
        if form is None:
            raise RuntimeError("UI 파일 로드 실패: sidebar.ui")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(form)
        self.form = form
        self.new_button = self.form.newChatButton
        self.list = self.form.sessionList
        self.rename_button = self.form.renameButton
        self.delete_button = self.form.deleteButton
        self.settings_button = self.form.settingsButton
        self.rename_button.setObjectName("subtleButton")
        self.delete_button.setObjectName("subtleDangerButton")
        self.list.currentItemChanged.connect(self._selection_changed)
        self.list.itemChanged.connect(self._rename_changed)
        self.rename_button.clicked.connect(self._start_rename)
        self.delete_button.clicked.connect(self._delete_current)
        self.new_button.clicked.connect(self.newChatRequested.emit)
        self.settings_button.clicked.connect(self.settingsRequested.emit)

    def set_sessions(self, sessions, selected_id=None):
        self.list.blockSignals(True)
        self.list.clear()
        for session in sessions:
            item = QListWidgetItem(session.title or "새 대화")
            item.setData(Qt.ItemDataRole.UserRole, session.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, session.status)
            if session.status != "generating":
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setToolTip(
                f"{session.title or '새 대화'}\n생성 중인 대화는 삭제할 수 없습니다."
                if session.status == "generating"
                else (session.title or "새 대화")
            )
            self.list.addItem(item)
            self._decorate_item(item, session.status)
        self.list.blockSignals(False)
        if selected_id:
            for i in range(self.list.count()):
                if self.list.item(i).data(Qt.ItemDataRole.UserRole) == selected_id:
                    self.list.setCurrentRow(i)
                    self._update_action_state(self.list.item(i))
                    return
        if self.list.count():
            self.list.setCurrentRow(0)
            self._update_action_state(self.list.item(0))
        else:
            self.rename_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def _update_action_state(self, item):
        if not item:
            self.rename_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        status = str(item.data(Qt.ItemDataRole.UserRole + 1) or "idle")
        generating = status == "generating"
        self.rename_button.setEnabled(not generating)
        self.delete_button.setEnabled(not generating)
        self.delete_button.setToolTip("생성 중인 대화는 삭제할 수 없습니다." if generating else "현재 대화 삭제")
        self.rename_button.setToolTip("생성 중인 대화는 이름을 변경할 수 없습니다." if generating else "대화 이름 변경")

    def add_session(self, session):
        self.set_sessions([session], session.id)

    def _decorate_item(self, item, status):
        suffix = {"generating": "  ⟳", "failed": "  !", "cancelled": "  ·"}.get(status, "")
        if suffix and not item.text().endswith(suffix):
            item.setText(item.text().rstrip() + suffix)

    def _selection_changed(self, current, previous):
        self._update_action_state(current)
        if current:
            self.sessionSelected.emit(str(current.data(Qt.ItemDataRole.UserRole)))

    def _start_rename(self):
        item = self.list.currentItem()
        if item and str(item.data(Qt.ItemDataRole.UserRole + 1) or "") != "generating":
            self.list.editItem(item)

    def _delete_current(self):
        item = self.list.currentItem()
        if item and str(item.data(Qt.ItemDataRole.UserRole + 1) or "") != "generating":
            self.sessionDeleteRequested.emit(str(item.data(Qt.ItemDataRole.UserRole)))

    def _rename_changed(self, item):
        session_id = str(item.data(Qt.ItemDataRole.UserRole))
        title = item.text().strip().rstrip("⟳!·").strip()
        if title:
            self.sessionRenamed.emit(session_id, title)
