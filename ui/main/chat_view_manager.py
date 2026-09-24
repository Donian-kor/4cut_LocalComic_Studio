# -*- coding: utf-8 -*-
"""ChatViewManager - 챗 뷰 생성/렌더링/카드 교체/위젯 캐시 로직 캡슐화."""

from PySide6.QtWidgets import QLabel

from core.models.chat import ChatMessageData
from ui.chat.chat_widgets import (
    ChatMessageRow,
    ChatScrollArea,
    GenerationCard,
    PanelResultCard,
    ResultCard,
    StoryPlanCard,
)
from ui.main.components.empty_state import EmptyState


class ChatViewManager:
    """채팅 뷰의 생성·렌더링·카드 교체·위젯 캐시 로직을 캡슐화한다.

    공개 속성:
        self.chat  -- ChatScrollArea 인스턴스
        self.empty -- EmptyState 인스턴스
        self._generation_widgets  -- message_id -> (row, card)
        self._result_widgets      -- message_id -> (row, card)
    """

    def __init__(self, on_save_comic=None, on_cancel=None,
                 on_regenerate=None, on_panel_regenerate=None,
                 on_panel_revision=None, parent=None):
        self._on_save_comic = on_save_comic
        self._on_cancel = on_cancel
        self._on_regenerate = on_regenerate
        self._on_panel_regenerate = on_panel_regenerate
        self._on_panel_revision = on_panel_revision

        self.chat = ChatScrollArea(parent)
        self.empty = EmptyState(parent)

        self._generation_widgets = {}  # message_id -> (row, card)
        self._result_widgets = {}      # message_id -> (row, card)
        self._parent = parent
        self._current_session = None

    def set_current_session(self, session):
        """MainWindow가 현재 세션을 전환할 때마다 호출한다."""
        self._current_session = session

    def _is_current_session(self, session):
        return (
            session is not None
            and self._current_session is not None
            and session.id == self._current_session.id
        )

    def render_session(self, session):
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
                        int(message.metadata.get("current", 0)), 4,
                    )
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
                card = PanelResultCard(
                    index, path,
                    dialogue=str(message.metadata.get("dialogue", "") or ""),
                    status=str(message.metadata.get("dialogue_status", "") or ""),
                )
                card.regenerateRequested.connect(self._on_panel_regenerate_wrapped)
                card.revisionRequested.connect(self._on_panel_revision_wrapped)
                row.bubble.layout.addWidget(card)
                self.chat.append(row)
                has_visible = True
            elif message.kind == "result":
                comic_stub = type(
                    "StoredComic", (),
                    {"title": session.title,
                     "output_path": message.metadata.get("result_path", session.result_path)},
                )()
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
        self.empty.setVisible(not has_visible)
        self.chat.setVisible(has_visible)

    def set_empty_visible(self, visible):
        self.empty.setVisible(visible)
        self.chat.setVisible(not visible)

    def add_ai_text(self, text):
        row = ChatMessageRow("ai")
        row.bubble.add_text(text)
        self.chat.append(row)

    def append_user_message(self, text, mood, art_style):
        """사용자 메시지 row를 생성해 채팅 뷰에 추가한다."""
        row = ChatMessageRow("user")
        row.bubble.add_text(text)
        meta = QLabel(f"분위기: {mood}   ·   그림체: {art_style}")
        meta.setObjectName("mutedText")
        row.bubble.layout.addWidget(meta)
        self.chat.append(row)
        self.set_empty_visible(False)


    def add_generation_message(self, session, initial="생성을 준비하는 중…", phase="story", panel_index=0):
        data = ChatMessageData(
            role="ai", kind="generation", text=initial,
            metadata={"phase": phase, "panel_index": int(panel_index or 0), "current": 0},
        )
        session.add_message(data)
        row = ChatMessageRow("ai")
        card = GenerationCard()
        card.cancelRequested.connect(self._on_cancel_wrapped)
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
        return data.id

    def add_panel_compose_message(self, session):
        return self.add_generation_message(session, initial="4컷 최종 합성중…", phase="compose")

    def begin_panel_generation(self, message_id, message, panel_index):
        row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, max(0, panel_index - 1), 4)
            card.set_panel_active(panel_index)

    def begin_final_composition(self, message_id, message):
        row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, 4, 4)
            card.set_compose_mode()

    def update_generation(self, message_id, message, current, total):
        row, card = self._generation_entry(message_id)
        if card:
            card.set_status(message, current, total)


    def complete_story_plan(self, message_id, comic, session):
        if not session or not message_id:
            return
        item = next((m for m in session.messages if m.id == message_id), None)
        if item is None:
            return
        item.kind = "story_plan"
        item.text = "스토리 계획"
        item.metadata = self._story_summary(comic, session)
        session.touch()
        if self._is_current_session(session):
            row, card = self._generation_entry(message_id)
            if card:
                card.stop()
            if row:
                self.chat.remove_widget(row)
            self._generation_widgets.pop(message_id, None)
            plan_row = ChatMessageRow("ai")
            plan_row.bubble.layout.addWidget(StoryPlanCard(item.metadata))
            self.chat.append(plan_row)

    def restore_panel_result_message(self, message_id, panel_index, session):
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
        if self._is_current_session(session):
            self.render_session(session)


    def complete_panel_generation(self, message_id, index, path, dialogue="", dialogue_status="", session=None):
        if not session:
            return
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
        if self._is_current_session(session):
            entry = self._generation_widgets.pop(message_id, None)
            if entry:
                self.chat.remove_widget(entry[0])
                result_row = ChatMessageRow("ai")
                result_card = PanelResultCard(index, path, dialogue=dialogue, status=dialogue_status)
                result_card.regenerateRequested.connect(self._on_panel_regenerate_wrapped)
                result_card.revisionRequested.connect(self._on_panel_revision_wrapped)
                result_row.bubble.layout.addWidget(result_card)
                self.chat.append(result_row)

    def begin_panel_regeneration(self, panel_index, revision="", session=None):
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
        if self._is_current_session(session):
            self.render_session(session)
            row, card = self._generation_widgets.get(target.id, (None, None))
            if card:
                card.set_panel_active(int(panel_index))
        return target.id

    def finish_panel_regeneration(self, message_id, panel_index, comic, session=None):
        if not session:
            return
        row, card = self._generation_entry(message_id)
        if card:
            card.stop()
        if row and self._is_current_session(session):
            self.chat.remove_widget(row)
        self._generation_widgets.pop(message_id, None)
        session.messages = [m for m in session.messages if m.id != message_id]
        session.panel_paths = [p.image_path for p in getattr(comic, "panels", []) if getattr(p, "image_path", "")]
        session.result_path = str(getattr(comic, "output_path", "") or session.result_path)
        session.master_seed = int(getattr(comic, "master_seed", session.master_seed) or 0)
        session.character_prompt = str(getattr(comic, "character_prompt", session.character_prompt) or "")
        session.style_prompt = str(getattr(comic, "style_prompt", session.style_prompt) or "")
        session.generation_config = dict(getattr(comic, "generation_config", session.generation_config) or {})
        session.comic_data = comic.to_dict() if hasattr(comic, "to_dict") else dict(session.comic_data)
        panels = getattr(comic, "panels", [])
        idx = int(panel_index or 0)
        new_path, dialogue, status = "", "", ""
        if 1 <= idx <= len(panels):
            panel = panels[idx - 1]
            new_path = str(getattr(panel, "image_path", "") or "")
            dialogue = str(getattr(panel, "dialogue", "") or "")
            status = str(getattr(panel, "dialogue_status", "") or "")
        panel_msg = next(
            (m for m in session.messages
             if m.kind == "generation" and m.metadata.get("phase") == "panel_revision"
             and int(m.metadata.get("panel_index", 0) or 0) == idx),
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
        self._update_final_result_widget(session, comic)
        if panel_msg is not None and self._is_current_session(session):
            entry = self._generation_widgets.pop(panel_msg.id, None)
            if entry:
                self.chat.remove_widget(entry[0])
            result_row = ChatMessageRow("ai")
            result_card = PanelResultCard(idx, new_path, dialogue=dialogue, status=status)
            result_card.regenerateRequested.connect(self._on_panel_regenerate_wrapped)
            result_card.revisionRequested.connect(self._on_panel_revision_wrapped)
            result_row.bubble.layout.addWidget(result_card)
            self.chat.append(result_row)


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
        if self._is_current_session(session):
            entry = self._result_widgets.get(result_message.id)
            if entry:
                row, card = entry
                card.update_result(comic)
            else:
                row = ChatMessageRow("ai")
                result_card = ResultCard(comic)
                result_card.saveRequested.connect(self._on_save_wrapped)
                result_card.regenerateRequested.connect(self._on_regenerate_wrapped)
                row.bubble.layout.addWidget(result_card)
                self.chat.append(row)
                self._result_widgets[result_message.id] = (row, result_card)

    def finish_generation(self, message_id, comic, session=None):
        if not session:
            return
        if message_id:
            row, card = self._generation_entry(message_id)
            if card:
                card.stop()
            if row and self._is_current_session(session):
                self.chat.remove_widget(row)
            self._generation_widgets.pop(message_id, None)
        session.status = "completed"
        session.result_path = comic.output_path or ""
        session.master_seed = int(getattr(comic, "master_seed", session.master_seed) or 0)
        session.character_prompt = str(getattr(comic, "character_prompt", session.character_prompt) or "")
        session.style_prompt = str(getattr(comic, "style_prompt", session.style_prompt) or "")
        session.generation_config = dict(getattr(comic, "generation_config", session.generation_config) or {})
        session.comic_data = comic.to_dict() if hasattr(comic, "to_dict") else session.comic_data
        session.panel_paths = [p.image_path for p in getattr(comic, "panels", []) if getattr(p, "image_path", "")]
        item = next((m for m in session.messages if m.id == message_id), None)
        if item and item.kind == "generation":
            item.text = "4컷 생성이 완료되었습니다."
            item.metadata["phase"] = "compose"
            item.metadata["current"] = 4
        result = ChatMessageData(
            role="ai", kind="result", text="완성",
            metadata={"result_path": session.result_path},
        )
        session.add_message(result)
        if self._is_current_session(session):
            row = ChatMessageRow("ai")
            result_card = ResultCard(comic)
            result_card.saveRequested.connect(self._on_save_wrapped)
            result_card.regenerateRequested.connect(self._on_regenerate_wrapped)
            row.bubble.layout.addWidget(result_card)
            self.chat.append(row)
        self._generation_widgets.clear()

    def fail_generation(self, message_id, message, session=None):
        if not session:
            return
        if self._is_current_session(session):
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

    def cancel_generation_ui(self, message_id, session=None):
        if not session:
            return
        if self._is_current_session(session):
            row, card = self._generation_entry(message_id)
            if card:
                card.set_cancelled()
        session.status = "cancelled"
        item = next((m for m in session.messages if m.id == message_id), None)
        if item:
            item.text = "생성이 취소되었습니다."
            item.metadata["cancelled"] = True
        session.touch()


    def _generation_entry(self, message_id):
        entry = self._generation_widgets.get(message_id)
        if not entry:
            return None, None
        return entry

    @staticmethod
    def _panel_result_text(index, status):
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
        return f"{index}컷 이미지와 대사 합성이 완료되었습니다."

    @staticmethod
    def _story_summary(comic, session):
        character = getattr(comic, "character", None)
        return {
            "title": str(getattr(comic, "title", "") or "4컷 스토리 계획"),
            "mood": str(getattr(session, "mood", "") or ""),
            "art_style": str(getattr(session, "art_style", "") or ""),
            "style": str(getattr(comic, "style", "") or ""),
            "character": {
                "name": str(getattr(character, "name", "") or ""),
                "appearance": str(getattr(character, "appearance", "") or ""),
                "personality": str(getattr(character, "personality", "") or ""),
            },
            "panels": [
                {
                    "scene": str(getattr(panel, "scene", "") or ""),
                    "dialogue": str(getattr(panel, "dialogue", "") or ""),
                    "speaker": str(getattr(panel, "speaker", "") or ""),
                }
                for panel in getattr(comic, "panels", [])
            ],
        }

    def _on_save_wrapped(self, comic):
        if self._on_save_comic:
            self._on_save_comic(comic)

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
