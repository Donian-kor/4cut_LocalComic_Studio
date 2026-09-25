# -*- coding: utf-8 -*-
"""채팅 화면 전용 렌더러. 세션 데이터는 읽기만 하고 직접 변경하지 않는다."""

from PySide6.QtWidgets import QLabel, QVBoxLayout

from studio.models.chat import ChatMessageData
from studio.ui.chat_widgets import ChatMessageRow, ChatScrollArea, GenerationCard, PanelResultCard, ResultCard, StoryPlanCard
from studio.ui.empty_state import EmptyState


class ChatViewManager:
    """ChatScrollArea와 동적 카드의 생성/갱신/교체만 담당한다."""

    def __init__(self, on_save_comic=None, on_cancel=None, on_regenerate=None, on_panel_regenerate=None,
                 on_panel_revision=None, chat_parent=None, empty_parent=None):
        self._on_save_comic = on_save_comic
        self._on_cancel = on_cancel
        self._on_regenerate = on_regenerate
        self._on_panel_regenerate = on_panel_regenerate
        self._on_panel_revision = on_panel_revision
        self.chat_parent = chat_parent
        self.empty_parent = empty_parent
        self.chat = ChatScrollArea(chat_parent)
        self.empty = EmptyState(empty_parent)
        self._generation_widgets = {}
        self._result_widgets = {}
        self._current_session = None
        self._install(self.chat, chat_parent)
        self._install(self.empty, empty_parent)
        # 첫 화면은 빈 상태만 보이고 채팅 Host는 접어 둔다(반반 분할 방지).
        self.set_empty_visible(True)

    @staticmethod
    def _install(widget, host):
        if host is None:
            return
        layout = host.layout()
        if layout is None:
            layout = QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    def set_current_session(self, session):
        self._current_session = session

    def _is_current_session(self, session):
        return bool(session and self._current_session and session.id == self._current_session.id)

    def render_session(self, session):
        self._current_session = session
        self.chat.clear_messages()
        self._generation_widgets.clear()
        self._result_widgets.clear()
        has_visible = False
        for message in session.messages:
            if message.kind == "text":
                row = ChatMessageRow(message.role)
                row.bubble.add_text(message.text)
                if message.mood or message.art_style:
                    meta = QLabel(f"분위기: {message.mood or '자동'}   ·   그림체: {message.art_style or '캐주얼 만화'}")
                    meta.setObjectName("mutedText")
                    row.bubble.layout.addWidget(meta)
                self.chat.append(row)
                has_visible = True
            elif message.kind == "generation":
                row = ChatMessageRow("ai")
                card = GenerationCard()
                card.cancelRequested.connect(self._on_cancel_wrapped)
                row.bubble.layout.addWidget(card)
                self.chat.append(row)
                self._generation_widgets[message.id] = (row, card)
                phase = str(message.metadata.get("phase", "story"))
                if message.metadata.get("cancelled"):
                    card.set_cancelled()
                elif message.metadata.get("failed"):
                    card.set_failed(message.text)
                else:
                    card.set_status(message.text or "생성 상태", int(message.metadata.get("current", 0)), 4)
                    panel_index = int(message.metadata.get("panel_index", 0) or 0)
                    if phase in {"panel", "panel_revision"} and panel_index:
                        card.set_panel_active(panel_index)
                    elif phase == "compose":
                        card.set_compose_mode()
                    else:
                        card.set_story_mode()
                has_visible = True
            elif message.kind == "story_plan":
                row = ChatMessageRow("ai")
                row.bubble.layout.addWidget(StoryPlanCard(dict(message.metadata or {})))
                self.chat.append(row)
                has_visible = True
            elif message.kind == "panel_result":
                row = ChatMessageRow("ai")
                index = int(message.metadata.get("panel_index", 0) or 0)
                path = str(message.metadata.get("path", "") or "")
                card = PanelResultCard(index, path, dialogue=str(message.metadata.get("dialogue", "") or ""),
                                       status=str(message.metadata.get("dialogue_status", "") or ""))
                card.regenerateRequested.connect(self._on_panel_regenerate_wrapped)
                card.revisionRequested.connect(self._on_panel_revision_wrapped)
                row.bubble.layout.addWidget(card)
                self.chat.append(row)
                has_visible = True
            elif message.kind == "result":
                comic_stub = type("StoredComic", (), {
                    "title": session.title,
                    "output_path": message.metadata.get("result_path", session.result_path),
                })()
                row = ChatMessageRow("ai")
                card = ResultCard(comic_stub)
                card.saveRequested.connect(self._on_save_wrapped)
                card.regenerateRequested.connect(self._on_regenerate_wrapped)
                row.bubble.layout.addWidget(card)
                self.chat.append(row)
                self._result_widgets[message.id] = (row, card)
                has_visible = True
            elif message.kind == "error":
                row = ChatMessageRow("ai")
                row.bubble.add_text(message.text or "생성에 실패했습니다.")
                self.chat.append(row)
                has_visible = True
        self.set_empty_visible(not has_visible)

    def set_empty_visible(self, visible):
        self.empty.setVisible(visible)
        self.chat.setVisible(not visible)
        # 컨테이너 자체도 토글해야 레이아웃 stretch 공간이 재분배된다.
        if self.empty_parent is not None:
            self.empty_parent.setVisible(visible)
        if self.chat_parent is not None:
            self.chat_parent.setVisible(not visible)

    def add_ai_text(self, text):
        row = ChatMessageRow("ai")
        row.bubble.add_text(text)
        self.chat.append(row)
        self.set_empty_visible(False)

    def append_user_message(self, text, mood, art_style):
        row = ChatMessageRow("user")
        row.bubble.add_text(text)
        meta = QLabel(f"분위기: {mood}   ·   그림체: {art_style}")
        meta.setObjectName("mutedText")
        row.bubble.layout.addWidget(meta)
        self.chat.append(row)
        self.set_empty_visible(False)

    def show_generation_message(self, data: ChatMessageData):
        row = ChatMessageRow("ai")
        card = GenerationCard()
        card.cancelRequested.connect(self._on_cancel_wrapped)
        row.bubble.layout.addWidget(card)
        self.chat.append(row)
        self._generation_widgets[data.id] = (row, card)
        card.start()
        phase = str(data.metadata.get("phase", "story"))
        panel_index = int(data.metadata.get("panel_index", 0) or 0)
        if phase == "panel" and panel_index:
            card.set_panel_active(panel_index)
        elif phase == "compose":
            card.set_compose_mode()
        else:
            card.set_story_mode()
        self.set_empty_visible(False)
        return data.id

    def begin_panel_generation(self, message_id, message, panel_index):
        _row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, max(0, panel_index - 1), 4)
            card.set_panel_active(panel_index)

    def begin_final_composition(self, message_id, message):
        _row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, 4, 4)
            card.set_compose_mode()

    def update_generation(self, message_id, message, current, total):
        _row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, current, total)

    def show_story_plan(self, message_id, summary):
        row, card = self._generation_entry(message_id)
        if card:
            card.stop()
        if row:
            self.chat.remove_widget(row)
        self._generation_widgets.pop(message_id, None)
        plan_row = ChatMessageRow("ai")
        plan_row.bubble.layout.addWidget(StoryPlanCard(dict(summary or {})))
        self.chat.append(plan_row)

    def complete_panel_generation(self, message_id, index, path, dialogue="", dialogue_status=""):
        entry = self._generation_widgets.pop(message_id, None)
        if entry:
            self.chat.remove_widget(entry[0])
        result_row = ChatMessageRow("ai")
        result_card = PanelResultCard(index, path, dialogue=dialogue, status=dialogue_status)
        result_card.regenerateRequested.connect(self._on_panel_regenerate_wrapped)
        result_card.revisionRequested.connect(self._on_panel_revision_wrapped)
        result_row.bubble.layout.addWidget(result_card)
        self.chat.append(result_row)

    def begin_panel_regeneration(self, session):
        self.render_session(session)

    def restore_panel_result_message(self, session):
        self.render_session(session)

    def finish_generation(self, session, comic=None, message_id=None):
        self.render_session(session)
        if comic is not None:
            result_message = next((m for m in reversed(session.messages) if m.kind == "result"), None)
            if result_message is not None:
                entry = self._result_widgets.get(result_message.id)
                if entry:
                    entry[1].update_result(comic)

    def finish_panel_regeneration(self, session, comic=None, panel_index=None):
        self.render_session(session)

    def fail_generation(self, message_id, message, session=None):
        _row, card = self._generation_entry(message_id)
        if card:
            card.set_failed(message)
        if session and self._is_current_session(session) and message_id:
            # 데이터 상태는 Controller가 커밋하므로 화면은 현재 세션을 다시 그려 일관성을 회복한다.
            self.render_session(session)

    def cancel_generation_ui(self, message_id, session=None):
        _row, card = self._generation_entry(message_id)
        if card:
            card.set_cancelled()
        if session and self._is_current_session(session):
            self.render_session(session)

    def _generation_entry(self, message_id):
        return self._generation_widgets.get(message_id, (None, None))

    @staticmethod
    def _on_save_wrapped_factory(callback, value):
        if callback:
            callback(value)

    def _on_save_wrapped(self, comic):
        self._on_save_wrapped_factory(self._on_save_comic, comic)

    def _on_cancel_wrapped(self):
        if self._on_cancel:
            self._on_cancel()

    def _on_regenerate_wrapped(self):
        if self._on_regenerate:
            self._on_regenerate()

    def _on_panel_regenerate_wrapped(self, panel_index):
        if self._on_panel_regenerate:
            self._on_panel_regenerate(panel_index)

    def _on_panel_revision_wrapped(self, panel_index, revision):
        if self._on_panel_revision:
            self._on_panel_revision(panel_index, revision)
