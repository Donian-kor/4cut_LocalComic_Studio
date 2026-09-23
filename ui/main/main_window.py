from datetime import datetime
from pathlib import Path
import shutil

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from settings.settings_window import SettingsWindow
from core.models.chat import ChatMessageData, ChatSession
from core.services.session_manager import SessionManager
from ui.chat.chat_widgets import ChatMessageRow, GenerationCard, PanelResultCard, ResultCard, ChatScrollArea
from ui.idea.idea_section import IdeaSection
from app.version import APP_NAME, APP_VERSION


class ServerStatusWorker(QThread):
    checked = Signal(bool, bool, str)

    def __init__(self, lm_factory, comfy_factory, settings_manager, parent=None):
        super().__init__(parent)
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.settings_manager = settings_manager

    def run(self):
        lm_ok = False
        comfy_ok = False
        errors = []
        try:
            lm = self.lm_factory(dict(self.settings_manager.section("lmstudio")))
            lm.test_connection(timeout=2)
            lm_ok = True
        except Exception as e:
            errors.append(f"LM Studio: {e}")
        try:
            comfy = self.comfy_factory(dict(self.settings_manager.section("comfyui")))
            comfy.test_connection(timeout=2)
            comfy_ok = True
        except Exception as e:
            errors.append(f"ComfyUI: {e}")
        self.checked.emit(lm_ok, comfy_ok, " / ".join(errors))


class Sidebar(QFrame):
    newChatRequested = Signal()
    sessionSelected = Signal(str)
    sessionDeleteRequested = Signal(str)
    settingsRequested = Signal()
    sessionRenamed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        self.new_button = QPushButton("＋  새 채팅")
        self.new_button.setObjectName("newChatButton")
        self.new_button.clicked.connect(self.newChatRequested.emit)
        layout.addWidget(self.new_button)

        label = QLabel("대화")
        label.setObjectName("sidebarSectionLabel")
        layout.addWidget(label)

        self.list = QListWidget()
        self.list.setObjectName("sessionList")
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.setEditTriggers(QListWidget.EditTrigger.DoubleClicked | QListWidget.EditTrigger.EditKeyPressed)
        self.list.currentItemChanged.connect(self._selection_changed)
        self.list.itemChanged.connect(self._rename_changed)
        layout.addWidget(self.list, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.rename_button = QPushButton("이름 변경")
        self.rename_button.setObjectName("subtleButton")
        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("subtleDangerButton")
        bottom.addWidget(self.rename_button)
        bottom.addWidget(self.delete_button)
        self.rename_button.clicked.connect(self._start_rename)
        self.delete_button.clicked.connect(self._delete_current)
        layout.addLayout(bottom)

        self.settings_button = QPushButton("⚙  설정")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        layout.addWidget(self.settings_button)

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


class EmptyState(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 32)
        layout.setSpacing(10)
        icon = QLabel("✦")
        icon.setObjectName("emptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("무엇을 만들어볼까요?")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("아이디어를 입력하면 스토리 → 이미지 → 대사 → 4컷 완성까지 AI가 진행합니다.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("emptySubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)


class Composer(QFrame):
    submitted = Signal(str, str, str, str)

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("composerFrame")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)

        self.idea = QPlainTextEdit()
        self.idea.setObjectName("composerEdit")
        self.idea.setPlaceholderText("아이디어를 입력하세요…  예: 퇴근하려는데 상사가 갑자기 춤을 추는 회사 개그 4컷")
        two_line_height = (self.idea.fontMetrics().lineSpacing() * 2) + 30
        self.idea.setMinimumHeight(two_line_height)
        self.idea.setMaximumHeight(two_line_height)
        self.idea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.idea.setTabChangesFocus(False)
        layout.addWidget(self.idea)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.mood = QComboBox()
        self.mood.setObjectName("composerCombo")
        self.mood.addItems(list(IdeaSection.STYLE_PRESETS.keys()))
        self.art = QComboBox()
        self.art.setObjectName("composerCombo")
        self.art.addItems(list(IdeaSection.ART_STYLE_PRESETS.keys()))
        bottom.addWidget(QLabel("분위기"))
        bottom.addWidget(self.mood)
        bottom.addWidget(QLabel("그림체"))
        bottom.addWidget(self.art)
        bottom.addStretch(1)
        self.send = QPushButton("↑")
        self.send.setObjectName("sendButton")
        self.send.setToolTip("전송")
        self.send.clicked.connect(self._submit)
        bottom.addWidget(self.send)
        layout.addLayout(bottom)
        self.idea.installEventFilter(self)
        self.setEnabled(True)

    def eventFilter(self, obj, event):
        if obj is self.idea and event.type() == event.Type.KeyPress:
            from PySide6.QtCore import Qt as _Qt
            if event.key() in (_Qt.Key.Key_Return, _Qt.Key.Key_Enter) and not (event.modifiers() & _Qt.KeyboardModifier.ShiftModifier):
                self._submit()
                return True
        return super().eventFilter(obj, event)

    def _submit(self):
        text = self.idea.toPlainText().strip()
        if not text:
            self.idea.setFocus()
            return
        mood = self.mood.currentText() or "자동"
        art = self.art.currentText() or "캐주얼 만화"
        mood_prompt = IdeaSection.STYLE_PRESETS.get(mood, "")
        art_prompt = IdeaSection.ART_STYLE_PRESETS.get(art, "")
        style_prompt = ", ".join([x for x in (art_prompt, mood_prompt) if x])
        self.submitted.emit(text, style_prompt, mood, art)

    def set_busy(self, busy):
        self.idea.setEnabled(not busy)
        self.mood.setEnabled(not busy)
        self.art.setEnabled(not busy)
        self.send.setEnabled(not busy)
        self.send.setText("…" if busy else "↑")

    def load_session_options(self, session):
        self.mood.setCurrentText(session.mood or "자동")
        self.art.setCurrentText(session.art_style or "캐주얼 만화")


class MainWindow(QMainWindow):
    settingsApplied = Signal()
    generationRequested = Signal(str, str, str, str)  # idea, style_prompt, mood label, art label
    cancelRequested = Signal()
    regenerateRequested = Signal()
    revisionRequested = Signal(str)
    panelRegenerateRequested = Signal(int)
    panelRevisionRequested = Signal(int, str)

    DARK_QSS = """
    * { font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif; }
    QMainWindow, QWidget { background: #0b0d13; color: #f5f7fb; }
    QFrame#headerFrame { background: #10131c; border-bottom: 1px solid #252a38; }
    QLabel#logoLabel { color: #fff; font-size: 20px; font-weight: 800; }
    QLabel#saveStatusLabel { color: #cbd2e1; font-size: 14px; font-weight: 800; padding: 6px 10px; background: #151a24; border: 1px solid #293043; border-radius: 8px; }
    QLabel#saveStatusLabel[state="busy"] { color: #d6d8ff; border-color: #4b50a2; background: #171a2f; }
    QLabel#saveStatusLabel[state="done"] { color: #84e6ad; border-color: #256a47; background: #10241b; }
    QLabel#saveStatusLabel[state="error"] { color: #fda4af; border-color: #713744; background: #2a171e; }
    QLabel#saveStatusLabel[state="checking"] { color: #cbd2e1; }
    QLabel#saveStatusLabel[state="connected"] { color: #cbd2e1; }
    QFrame#sidebar { background: #10131c; border-right: 1px solid #252a38; }
    QLabel#sidebarSectionLabel { color: #737c8f; font-size: 11px; font-weight: 800; padding: 3px 4px; }
    QPushButton { background: #1a1f2c; color: #e8ebf2; border: 1px solid #303748; border-radius: 9px; padding: 9px 13px; font-weight: 600; }
    QPushButton:hover { background: #22283a; border-color: #59627a; }
    QPushButton:disabled { color: #646b7a; background: #141720; border-color: #222735; }
    QPushButton#newChatButton { background: #6366f1; border: none; color: #fff; font-weight: 800; }
    QPushButton#settingsButton { border: 1px solid #252a38; background: #141822; color: #aab1c0; text-align: left; }
    QPushButton#subtleButton, QPushButton#subtleDangerButton { padding: 7px 9px; font-size: 11px; }
    QPushButton#subtleDangerButton:hover { border-color: #7f3440; color: #fca5a5; }
    QListWidget#sessionList { background: transparent; border: none; outline: none; }
    QListWidget#sessionList::item { padding: 11px 10px; margin: 1px 0; border-radius: 8px; color: #aeb5c4; }
    QListWidget#sessionList::item:hover { background: #171c27; color: #fff; }
    QListWidget#sessionList::item:selected { background: #242946; color: #fff; }
    QScrollArea { background: #0b0d13; }
    QFrame#composerFrame { background: #10131c; border-top: 1px solid #252a38; }
    QPlainTextEdit#composerEdit { background: #151923; border: 1px solid #303748; border-radius: 12px; color: #f5f7fb; padding: 12px; font-size: 14px; }
    QPlainTextEdit#composerEdit:focus { border-color: #6366f1; }
    QComboBox#composerCombo { min-width: 100px; padding: 6px 9px; }
    QPushButton#sendButton { min-width: 42px; min-height: 38px; padding: 0; background: #6366f1; border: none; color: #fff; font-size: 18px; }
    QLabel#aiBadge, QLabel#userBadge { min-width: 44px; padding-top: 6px; color: #818cf8; font-size: 11px; font-weight: 800; }
    QLabel#userBadge { color: #9ca3af; }
    QFrame#chatBubbleAi { background: #151923; border: 1px solid #292f40; border-radius: 14px; }
    QFrame#chatBubbleUser { background: #242946; border: 1px solid #363d67; border-radius: 14px; }
    QLabel#mutedText { color: #8a92a3; }
    QFrame#generationCard { background: #121620; border: 1px solid transparent; border-radius: 12px; }
    QLabel#generationStatus { color: #e4e8f1; font-size: 14px; font-weight: 700; }
    QLabel#generationTimer { color: #818cf8; font-size: 12px; font-weight: 700; }
    QLabel#generationPanelBadge { color: #c7cbff; background: #1a1d35; border: 1px solid #343962; border-radius: 999px; padding: 5px 12px; font-size: 11px; font-weight: 800; }
    QLabel#generationPreviewTitle { color: #f2f4ff; font-size: 20px; font-weight: 800; }
    QLabel#generationPreviewText { color: #8d96aa; font-size: 12px; }
    QFrame#generationPreview { background: #0e121a; border: 1px solid #252b3a; border-radius: 12px; min-height: 170px; }
    QLabel#generationStep { color: #858ea0; font-size: 11px; }
    QProgressBar { background: #1b202b; border: none; border-radius: 4px; }
    QProgressBar::chunk { background: #6366f1; border-radius: 4px; }
    QFrame#panelResultCard { background: #121820; border: 1px solid #2b3140; border-radius: 12px; }
    QLabel#panelResultTitle { color: #fff; font-size: 15px; font-weight: 800; }
    QLabel#panelDoneBadge { color: #83e2bd; background: #10261e; border: 1px solid #1d634b; border-radius: 999px; padding: 5px 10px; font-size: 10px; font-weight: 800; }
    QLabel#panelResultImage { background: #0e1118; border: 1px solid #252b3a; border-radius: 10px; }
    QLabel#panelDialogueText { color: #c6ccda; background: #151a24; border: 1px solid #2b3140; border-radius: 8px; padding: 8px 10px; font-size: 12px; }
    QPushButton#dangerButton { background: #332029; border-color: #6a3442; color: #fda4af; }
    QFrame#resultCard { background: #121620; border: 1px solid #2b3140; border-radius: 12px; }
    QLabel#resultTitle { font-size: 15px; font-weight: 800; color: #fff; }
    QLabel#finalComicImage { background: #0e1118; border: 1px solid #252b3a; border-radius: 10px; }
    QPushButton#primaryAction { background: #2a2f5d; border-color: #4b50a2; color: #e6e7ff; }
    QFrame#emptyState { background: transparent; }
    QLabel#emptyIcon { color: #6366f1; font-size: 40px; }
    QLabel#emptyTitle { color: #fff; font-size: 22px; font-weight: 800; }
    QLabel#emptySubtitle { color: #838c9e; font-size: 13px; }
    QStatusBar { background: #10131c; color: #7d8597; }
    """

    def __init__(self, settings_manager, lm_factory, comfy_factory, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1200, 820)
        self.setMinimumSize(960, 700)
        self.setStyleSheet(self.DARK_QSS)

        self.session_manager = SessionManager(settings_manager)
        self.current_session = None
        self._server_worker = None
        self._server_state = (False, False)
        self._generation_widgets = {}  # message_id -> (row, card)
        self._result_widgets = {}  # message_id -> (row, card)
        self._generating_session_id = None

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        root_layout.addWidget(self._build_header())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.sidebar = Sidebar()
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(360)
        splitter.addWidget(self.sidebar)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.chat = ChatScrollArea()
        self.empty = EmptyState()
        self.composer = Composer(settings_manager)
        main_layout.addWidget(self.empty, 1)
        main_layout.addWidget(self.chat, 1)
        main_layout.addWidget(self.composer, 0)
        splitter.addWidget(main)
        splitter.setSizes([260, 940])
        root_layout.addWidget(splitter, 1)

        self.form = type("FormProxy", (), {})()
        self.form.settingsButton = None
        self.form.saveStatusLabel = self.status_label

        self.sidebar.newChatRequested.connect(self.new_chat)
        self.sidebar.sessionSelected.connect(self.open_session)
        self.sidebar.sessionDeleteRequested.connect(self.delete_session)
        self.sidebar.sessionRenamed.connect(self.rename_session)
        self.sidebar.settingsRequested.connect(self.open_settings)
        self.composer.submitted.connect(self.generationRequested.emit)

        # 메인 입력창은 공통 Composer를 사용하므로 하위 화면들의 중복 입력창을 만들지 않는다.
        self.statusBar().showMessage("새 채팅을 시작해 보세요.")
        self._refresh_sidebar()
        if not self.session_manager.sessions:
            self.new_chat(auto=True)
        else:
            self.open_session(self.session_manager.sessions[0].id)
        self.refresh_server_status()

    def closeEvent(self, event):
        # 종료 시 대기 중인 디바운스 세션 저장을 즉시 커밋한다.
        try:
            self.session_manager.flush()
        except Exception:
            pass
        super().closeEvent(event)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(64)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 20, 0)
        layout.setSpacing(12)
        logo = QLabel(f"✦ 4cut Studio <span style='font-size:12px; font-weight:700; color:#8b93a7'>{APP_VERSION}</span>")
        logo.setObjectName("logoLabel")
        layout.addWidget(logo)
        self.status_label = QLabel("● AI 서버 확인 중...")
        self.status_label.setObjectName("saveStatusLabel")
        self._set_status_label("● AI 서버 확인 중...", "checking")
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        return header

    def _set_status_label(self, text, state="connected"):
        self.status_label.setText(text)
        self.status_label.setProperty("state", state)
        style = self.status_label.style()
        style.unpolish(self.status_label)
        style.polish(self.status_label)
        self.status_label.update()

    def _refresh_sidebar(self):
        selected = self.current_session.id if self.current_session else None
        self.sidebar.set_sessions(self.session_manager.sessions, selected)

    def new_chat(self, auto=False):
        if self.current_session and not auto and not self.current_session.messages:
            self.open_session(self.current_session.id)
            return
        session = ChatSession()
        session.add_message(ChatMessageData(role="ai", kind="text", text="안녕하세요! 아이디어를 입력하면 스토리부터 4컷 완성까지 도와드릴게요."))
        self.session_manager.add(session)
        self.current_session = session
        self._refresh_sidebar()
        self._render_session(session)
        self.composer.idea.clear()
        self.composer.load_session_options(session)
        self.composer.set_busy(False)
        self.statusBar().showMessage("새 대화가 시작되었습니다.")

    def open_session(self, session_id):
        session = self.session_manager.get(session_id)
        if not session:
            return
        self.current_session = session
        self._render_session(session)
        self.composer.load_session_options(session)
        self.composer.idea.clear()
        # 생성 중인 세션은 입력을 잠그고, 다른 세션으로 이동해도 전역 생성 중 상태를 유지한다.
        self.composer.set_busy(self._generating_session_id is not None)
        self.statusBar().showMessage(
            "현재 대화에서 생성 중입니다." if session.status == "generating" else "대화를 열었습니다.",
            2000,
        )

    def delete_session(self, session_id):
        session = self.session_manager.get(session_id)
        if not session:
            return
        if session.status == "generating":
            QMessageBox.information(self, "삭제할 수 없음", "생성 중인 대화는 생성이 끝나거나 취소될 때까지 삭제할 수 없습니다.")
            self._refresh_sidebar()
            return
        answer = QMessageBox.question(
            self,
            "대화 삭제",
            f"'{session.title}' 대화를 삭제할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if not self.session_manager.remove(session_id):
            return
        if self.current_session and self.current_session.id == session_id:
            self.current_session = None
            if self.session_manager.sessions:
                self.open_session(self.session_manager.sessions[0].id)
            else:
                self.new_chat()
        else:
            self._refresh_sidebar()

    def rename_session(self, session_id, title):
        session = self.session_manager.get(session_id)
        if not session or session.status == "generating":
            return
        clean = " ".join(title.replace("⟳", "").replace("!", "").replace("·", "").split())[:40]
        if clean:
            session.title = clean
            session.touch()
            self.session_manager.update(session)
            if self.current_session and self.current_session.id == session.id:
                self.statusBar().showMessage(f"대화 이름을 '{clean}'으로 변경했습니다.", 2500)
            self._refresh_sidebar()

    def _render_session(self, session):
        self.chat.clear_messages()
        self._generation_widgets.clear()
        self._result_widgets.clear()
        has_visible = False
        for message in session.messages:
            if message.kind == "text":
                row = ChatMessageRow(message.role)
                row.bubble.add_text(message.text)
                if message.mood or message.art_style:
                    meta = QLabel(
                        f"분위기: {message.mood or '자동'}   ·   그림체: {message.art_style or '캐주얼 만화'}"
                    )
                    meta.setObjectName("mutedText")
                    row.bubble.layout.addWidget(meta)
                self.chat.append(row)
                has_visible = True

            elif message.kind == "generation":
                row = ChatMessageRow("ai")
                card = GenerationCard()
                row.bubble.layout.addWidget(card)
                self.chat.append(row)
                self._generation_widgets[message.id] = (row, card)
                phase = str(message.metadata.get("phase", "story"))
                if message.metadata.get("cancelled"):
                    card.set_cancelled()
                elif message.metadata.get("failed"):
                    card.set_failed(message.text)
                else:
                    card.set_status(
                        message.text or "생성 상태",
                        int(message.metadata.get("current", 0)),
                        4,
                    )
                    panel_index = int(message.metadata.get("panel_index", 0) or 0)
                    if phase in {"panel", "panel_revision"} and panel_index:
                        card.set_panel_active(panel_index)
                    elif phase == "compose":
                        card.set_compose_mode()
                    else:
                        card.set_story_mode()
                has_visible = True

            elif message.kind == "panel_result":
                row = ChatMessageRow("ai")
                index = int(message.metadata.get("panel_index", 0) or 0)
                path = str(message.metadata.get("path", "") or "")
                card = PanelResultCard(
                    index,
                    path,
                    dialogue=str(message.metadata.get("dialogue", "") or ""),
                    status=str(message.metadata.get("dialogue_status", "") or ""),
                )
                card.regenerateRequested.connect(self.panelRegenerateRequested.emit)
                card.revisionRequested.connect(self.panelRevisionRequested.emit)
                row.bubble.layout.addWidget(card)
                self.chat.append(row)
                has_visible = True

            elif message.kind == "result":
                comic_stub = type(
                    "StoredComic",
                    (),
                    {
                        "title": session.title,
                        "output_path": message.metadata.get("result_path", session.result_path),
                    },
                )()
                row = ChatMessageRow("ai")
                card = ResultCard(comic_stub)
                card.saveRequested.connect(self.save_comic)
                card.regenerateRequested.connect(self.regenerateRequested.emit)
                row.bubble.layout.addWidget(card)
                self.chat.append(row)
                self._result_widgets[message.id] = (row, card)
                has_visible = True

            elif message.kind == "error":
                row = ChatMessageRow("ai")
                row.bubble.add_text(message.text or "생성에 실패했습니다.")
                self.chat.append(row)
                has_visible = True

        self.empty.setVisible(not has_visible)
        self.chat.setVisible(has_visible)

        if session.status == "generating":
            self.composer.set_busy(True)

    def ensure_user_message(self, text, mood, art_style, idea_value=None, update_title=True):
        session = self.current_session
        if session is None:
            self.new_chat()
            session = self.current_session
        message = ChatMessageData(role="user", kind="text", text=text, mood=mood, art_style=art_style)
        session.add_message(message)
        session.idea = idea_value if idea_value is not None else text
        session.mood = mood
        session.art_style = art_style
        if update_title:
            session.set_title_from_idea(text)
        self.session_manager.update(session)
        row = ChatMessageRow("user")
        row.bubble.add_text(text)
        meta = QLabel(f"분위기: {mood}   ·   그림체: {art_style}")
        meta.setObjectName("mutedText")
        row.bubble.layout.addWidget(meta)
        self.chat.append(row)
        self.empty.setVisible(False)
        self.chat.setVisible(True)
        return session

    def add_ai_text(self, text):
        row = ChatMessageRow("ai")
        row.bubble.add_text(text)
        self.chat.append(row)

    def add_generation_message(self, session, initial="생성을 준비하는 중…", phase="story", panel_index=0):
        data = ChatMessageData(
            role="ai",
            kind="generation",
            text=initial,
            metadata={
                "phase": phase,
                "panel_index": int(panel_index or 0),
                "current": 0,
            },
        )
        session.add_message(data)
        self.session_manager.update(session)

        row = ChatMessageRow("ai")
        card = GenerationCard()
        card.cancelRequested.connect(self.cancelRequested.emit)
        row.bubble.layout.addWidget(card)
        self.chat.append(row)
        self._generation_widgets[data.id] = (row, card)
        card.start()
        if phase == "panel" and panel_index:
            card.set_panel_active(int(panel_index))
        elif phase == "compose":
            card.set_compose_mode()
        else:
            card.set_story_mode()
        self.composer.set_busy(True)
        return data.id

    def _generation_entry(self, message_id):
        entry = self._generation_widgets.get(message_id)
        if not entry:
            return None, None
        return entry

    @staticmethod
    def _panel_result_text(index, status):
        """패널 결과 메시지 문구를 대사 합성 상태에 맞게 결정한다."""
        status = str(status or "")
        if status == "composited":
            return f"{index}컷 이미지와 대사 합성이 완료되었습니다."
        if status == "failed":
            return f"{index}컷 이미지가 완료되었지만 대사 합성에 실패했습니다. 최종 합성에서 대체 처리됩니다."
        if status == "skipped":
            return f"{index}컷 이미지가 완료되었습니다. (2단계 합성 미설정 — 최종 합성에서 대사를 그립니다)"
        if status == "fallback":
            return f"{index}컷 이미지와 대사(대체 합성)가 완료되었습니다."
        if status == "none":
            return f"{index}컷 이미지가 완료되었습니다."
        # 구버전 세션(상태 없음) 호환 문구
        return f"{index}컷 이미지와 대사 합성이 완료되었습니다."

    def restore_panel_result_message(self, message_id, panel_index, session_id=None):
        """재생성 실패/취소 시 덮어쓴 컷 메시지를 마지막 커밋본 결과로 복원한다.

        panel_paths/comic_data는 실패·취소 시점까지 보존되므로 그 값으로
        재구성하며, 세션 상태(실패/취소)는 호출한 fail/cancel 쪽이 관리한다.
        """
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        item = next((m for m in session.messages if m.id == message_id), None)
        if item is None:
            return
        index = int(panel_index or 0)
        path = ""
        if 1 <= index <= len(session.panel_paths):
            path = str(session.panel_paths[index - 1] or "")
        dialogue = ""
        status = ""
        panels = (session.comic_data or {}).get("panels") or []
        if 1 <= index <= len(panels):
            panel = panels[index - 1]
            dialogue = str(panel.get("dialogue") or "")
            status = str(panel.get("dialogue_status") or "")
            path = path or str(panel.get("image_path") or "")
        item.kind = "panel_result"
        item.text = self._panel_result_text(index, status)
        item.metadata = {
            "panel_index": index,
            "path": path,
            "dialogue": dialogue,
            "dialogue_status": status,
        }
        session.touch()
        self.session_manager.update(session)
        if self.current_session and self.current_session.id == session.id:
            # 실패/취소 카드를 유지한 채 복원된 컷 결과를 다시 그린다.
            self._render_session(session)

    def begin_panel_generation(self, message_id, index, message):
        row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, max(0, index - 1), 4)
            card.set_panel_active(index)
        session = self.session_manager.get(self._generating_session_id) if self._generating_session_id else self.current_session
        if session:
            item = next((m for m in session.messages if m.id == message_id), None)
            if item:
                item.text = message
                item.metadata.update({"phase": "panel", "panel_index": index, "current": max(0, index - 1)})
                session.touch()
                self.session_manager.update(session)

    def begin_final_composition(self, message_id, message):
        row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, 4, 4)
            card.set_compose_mode()
        session = self.session_manager.get(self._generating_session_id) if self._generating_session_id else self.current_session
        if session:
            item = next((m for m in session.messages if m.id == message_id), None)
            if item:
                item.text = message
                item.metadata.update({"phase": "compose", "current": 4})
                session.touch()
                self.session_manager.update(session)

    def add_panel_generation_message(self, session, index):
        return self.add_generation_message(
            session,
            initial=f"{index}컷 이미지 생성중…",
            phase="panel",
            panel_index=index,
        )

    def update_generation(self, message_id, message, current, total, session_id=None):
        row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, current, total)
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if session:
            item = next((m for m in session.messages if m.id == message_id), None)
            if item:
                item.text = message
                item.metadata["current"] = current
                session.touch()
                self.session_manager.update(session)

    def complete_panel_generation(self, message_id, index, path, dialogue="", dialogue_status="", session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if session:
            while len(session.panel_paths) < index:
                session.panel_paths.append("")
            session.panel_paths[index - 1] = path or ""
            item = next((m for m in session.messages if m.id == message_id), None)
            if item:
                item.kind = "panel_result"
                item.text = self._panel_result_text(index, dialogue_status)
                item.metadata = {
                    "panel_index": index,
                    "path": path or "",
                    "dialogue": dialogue or "",
                    "dialogue_status": str(dialogue_status or ""),
                }
            session.touch()
            self.session_manager.update(session)

            if self.current_session and self.current_session.id == session.id:
                row, card = self._generation_entry(message_id)
                if row:
                    self.chat.remove_widget(row)
                    self._generation_widgets.pop(message_id, None)
                    result_row = ChatMessageRow("ai")
                    result_card = PanelResultCard(index, path, dialogue=dialogue, status=dialogue_status)
                    result_card.regenerateRequested.connect(self.panelRegenerateRequested.emit)
                    result_card.revisionRequested.connect(self.panelRevisionRequested.emit)
                    result_row.bubble.layout.addWidget(result_card)
                    self.chat.append(result_row)

    def begin_panel_regeneration(self, panel_index, revision="", session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return None
        target = None
        for message in reversed(session.messages):
            if message.kind == "panel_result" and int(message.metadata.get("panel_index", 0) or 0) == int(panel_index):
                target = message
                break
        if target is None:
            return None
        target.kind = "generation"
        target.text = f"{panel_index}컷을 다시 생성하고 있습니다…"
        target.metadata = {
            "phase": "panel_revision",
            "panel_index": int(panel_index),
            "current": max(0, int(panel_index) - 1),
            "revision": revision or "",
        }
        session.status = "generating"
        session.error_message = ""
        session.touch()
        self.session_manager.update(session)
        self._generating_session_id = session.id
        if self.current_session and self.current_session.id == session.id:
            self._render_session(session)
            row, card = self._generation_widgets.get(target.id, (None, None))
            if card:
                card.set_panel_active(int(panel_index))
        self.composer.set_busy(True)
        self._set_status_label("● AI 작업 중", "busy")
        self._refresh_sidebar()
        return target.id

    def add_panel_compose_message(self, session):
        return self.add_generation_message(
            session,
            initial="4컷 최종 합성중…",
            phase="compose",
        )

    def finish_panel_regeneration(self, message_id, panel_index, comic, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return

        # 최종 합성용 임시 generation 메시지는 완료되면 제거한다.
        row, card = self._generation_entry(message_id)
        if card:
            card.stop()
        if row and self.current_session and self.current_session.id == session.id:
            self.chat.remove_widget(row)
        self._generation_widgets.pop(message_id, None)
        session.messages = [m for m in session.messages if m.id != message_id]

        session.panel_paths = [
            p.image_path for p in getattr(comic, "panels", []) if getattr(p, "image_path", "")
        ]
        session.result_path = str(getattr(comic, "output_path", "") or session.result_path)
        session.master_seed = int(getattr(comic, "master_seed", session.master_seed) or 0)
        session.character_prompt = str(getattr(comic, "character_prompt", session.character_prompt) or "")
        session.style_prompt = str(getattr(comic, "style_prompt", session.style_prompt) or "")
        session.generation_config = dict(getattr(comic, "generation_config", session.generation_config) or {})
        session.comic_data = comic.to_dict() if hasattr(comic, "to_dict") else dict(session.comic_data)

        # 재생성 시작 시 generation으로 바뀌었던 원래 컷 메시지를
        # 합성 성공본의 panel_result로 한 번에 전환한다(단일 커밋).
        panels = getattr(comic, "panels", [])
        idx = int(panel_index or 0)
        new_path, dialogue, status = "", "", ""
        if 1 <= idx <= len(panels):
            panel = panels[idx - 1]
            new_path = str(getattr(panel, "image_path", "") or "")
            dialogue = str(getattr(panel, "dialogue", "") or "")
            status = str(getattr(panel, "dialogue_status", "") or "")
        panel_msg = next(
            (
                m for m in session.messages
                if m.kind == "generation"
                and m.metadata.get("phase") == "panel_revision"
                and int(m.metadata.get("panel_index", 0) or 0) == idx
            ),
            None,
        )
        if panel_msg is not None:
            panel_msg.kind = "panel_result"
            panel_msg.text = self._panel_result_text(idx, status)
            panel_msg.metadata = {
                "panel_index": idx,
                "path": new_path,
                "dialogue": dialogue,
                "dialogue_status": status,
            }
        session.status = "completed"
        session.error_message = ""
        session.touch()
        self.session_manager.update(session)
        self._generating_session_id = None
        self.composer.set_busy(False)
        self._update_final_result_widget(session, comic)
        # 원래 컷 메시지의 진행 카드를 새 결과 카드로 교체한다.
        if panel_msg is not None and self.current_session and self.current_session.id == session.id:
            entry = self._generation_widgets.pop(panel_msg.id, None)
            if entry:
                self.chat.remove_widget(entry[0])
            result_row = ChatMessageRow("ai")
            result_card = PanelResultCard(idx, new_path, dialogue=dialogue, status=status)
            result_card.regenerateRequested.connect(self.panelRegenerateRequested.emit)
            result_card.revisionRequested.connect(self.panelRevisionRequested.emit)
            result_row.bubble.layout.addWidget(result_card)
            self.chat.append(result_row)
        self._refresh_sidebar()
        self._set_status_label("● 생성 완료", "done")
        self.statusBar().showMessage(f"{panel_index}컷 재생성과 최종 합성이 완료되었습니다.", 4000)

    def _update_final_result_widget(self, session, comic):
        result_message = None
        for message in reversed(session.messages):
            if message.kind == "result":
                result_message = message
                break
        if result_message is None:
            result_message = ChatMessageData(
                role="ai", kind="result", text="완성",
                metadata={"result_path": getattr(comic, "output_path", "") or ""},
            )
            session.add_message(result_message)
        else:
            result_message.metadata["result_path"] = getattr(comic, "output_path", "") or ""
            result_message.text = "완성"
        session.result_path = getattr(comic, "output_path", "") or session.result_path
        session.comic_data = comic.to_dict() if hasattr(comic, "to_dict") else session.comic_data
        session.touch()
        self.session_manager.update(session)
        if self.current_session and self.current_session.id == session.id:
            entry = self._result_widgets.get(result_message.id)
            if entry:
                row, card = entry
                card.update_result(comic)
            else:
                row = ChatMessageRow("ai")
                result_card = ResultCard(comic)
                result_card.saveRequested.connect(self.save_comic)
                result_card.regenerateRequested.connect(self.regenerateRequested.emit)
                row.bubble.layout.addWidget(result_card)
                self.chat.append(row)
                self._result_widgets[result_message.id] = (row, result_card)

    def finish_generation(self, message_id, comic, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        if message_id:
            row, card = self._generation_entry(message_id)
            if card:
                card.stop()
            if row and self.current_session and self.current_session.id == session.id:
                self.chat.remove_widget(row)
            self._generation_widgets.pop(message_id, None)

        session.status = "completed"
        session.result_path = comic.output_path or ""
        session.master_seed = int(getattr(comic, "master_seed", session.master_seed) or 0)
        session.character_prompt = str(getattr(comic, "character_prompt", session.character_prompt) or "")
        session.style_prompt = str(getattr(comic, "style_prompt", session.style_prompt) or "")
        session.generation_config = dict(getattr(comic, "generation_config", session.generation_config) or {})
        session.comic_data = comic.to_dict() if hasattr(comic, "to_dict") else session.comic_data
        session.panel_paths = [
            p.image_path for p in getattr(comic, "panels", []) if getattr(p, "image_path", "")
        ]
        # 진행 메시지가 아직 남아 있는 경우(구버전/예외 경로) 최종 상태로 남긴다.
        item = next((m for m in session.messages if m.id == message_id), None)
        if item and item.kind == "generation":
            item.text = "4컷 생성이 완료되었습니다."
            item.metadata["phase"] = "compose"
            item.metadata["current"] = 4
        result = ChatMessageData(
            role="ai",
            kind="result",
            text="완성",
            metadata={"result_path": session.result_path},
        )
        session.add_message(result)
        self.session_manager.update(session)

        if self.current_session and self.current_session.id == session.id:
            row = ChatMessageRow("ai")
            result_card = ResultCard(comic)
            result_card.saveRequested.connect(self.save_comic)
            result_card.regenerateRequested.connect(self.regenerateRequested.emit)
            row.bubble.layout.addWidget(result_card)
            self.chat.append(row)
        self.composer.set_busy(False)
        self._generation_widgets.clear()
        self._generating_session_id = None
        self._refresh_sidebar()
        self._set_status_label("● 생성 완료", "done")
        self.statusBar().showMessage("4컷 만화가 완성되었습니다.", 4000)

    def fail_generation(self, message_id, message, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        if self.current_session and self.current_session.id == session.id:
            row, card = self._generation_entry(message_id)
            if card:
                card.set_failed(message)
        session.status = "failed"
        session.error_message = message
        item = next((m for m in session.messages if m.id == message_id), None)
        if item:
            item.text = message
            item.metadata["failed"] = True
        session.touch()
        self.session_manager.update(session)
        self.composer.set_busy(False)
        self._generating_session_id = None
        self._set_status_label("● 생성 오류", "error")
        self._refresh_sidebar()

    def cancel_generation_ui(self, message_id, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        if self.current_session and self.current_session.id == session.id:
            row, card = self._generation_entry(message_id)
            if card:
                card.set_cancelled()
        session.status = "cancelled"
        item = next((m for m in session.messages if m.id == message_id), None)
        if item:
            item.text = "생성이 취소되었습니다."
            item.metadata["cancelled"] = True
        session.touch()
        self.session_manager.update(session)
        self.composer.set_busy(False)
        self._generating_session_id = None
        self._set_status_label("● AI 서버 연결됨" if all(self._server_state) else "● AI 서버 확인 필요", "connected" if all(self._server_state) else "error")
        self._refresh_sidebar()

    def mark_generating(self, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if session:
            session.status = "generating"
            session.error_message = ""
            session.touch()
            self.session_manager.update(session)
            self._generating_session_id = session.id
        self._set_status_label("● AI 작업 중", "busy")
        self.composer.set_busy(True)
        self._refresh_sidebar()

    def save_comic(self, comic):
        path = getattr(comic, "output_path", "")
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "저장할 이미지 없음", "완성된 4컷 이미지를 찾을 수 없습니다.")
            return
        target, _ = QFileDialog.getSaveFileName(self, "4컷 만화 저장", "4cut.png", "PNG (*.png)")
        if target:
            try:
                shutil.copy2(path, target)
                self.statusBar().showMessage(f"이미지를 저장했습니다: {target}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "저장 실패", str(e))

    def refresh_server_status(self):
        if self._server_worker and self._server_worker.isRunning():
            return
        self._set_status_label("● AI 서버 확인 중...", "checking")
        self._server_worker = ServerStatusWorker(self.lm_factory, self.comfy_factory, self.settings_manager, self)
        self._server_worker.checked.connect(self._on_server_status)
        self._server_worker.finished.connect(self._release_server_worker)
        self._server_worker.start()

    def _release_server_worker(self):
        self._server_worker = None

    def _on_server_status(self, lm_ok, comfy_ok, errors):
        self._server_state = (lm_ok, comfy_ok)
        if self._generating_session_id is not None:
            self._set_status_label("● AI 작업 중", "busy")
        elif lm_ok and comfy_ok:
            if self.current_session and self.current_session.status == "completed":
                self._set_status_label("● 생성 완료", "done")
            else:
                self._set_status_label("● AI 서버 연결됨", "connected")
        elif lm_ok or comfy_ok:
            self._set_status_label("● 일부 AI 서버 연결됨", "connected")
        else:
            self._set_status_label("● AI 서버 미연결", "error")
        if errors and self.current_session:
            self.statusBar().showMessage("AI 서버 연결을 확인하세요. 설정에서 주소와 연결 상태를 확인할 수 있습니다.", 6000)

    def open_settings(self):
        if getattr(self, "settings_dialog", None) is not None:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return
        try:
            self.settings_dialog = SettingsWindow(self.settings_manager, self.lm_factory, self.comfy_factory, self)
            result = self.settings_dialog.form.exec()
            if result:
                self.settingsApplied.emit()
                self._set_status_label("● 설정 저장됨 · 서버 확인 중...", "checking")
                self.statusBar().showMessage("설정이 저장되었습니다. 서버 연결을 다시 확인합니다.", 4000)
                self.refresh_server_status()
        except Exception as e:
            QMessageBox.critical(self, "설정창 오류", f"설정창을 열 수 없습니다.\n\n{e}")
        finally:
            self.settings_dialog = None
