from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QComboBox, QDialog, QFileDialog, QLabel, QListWidgetItem, QMessageBox
from studio.settings.model_manager import ImageModelManager
from studio.models.image_model import ImageModelProfile
from studio.services import workflow_factory
from studio.ui import theme


class ConnectionWorker(QThread):
    done = Signal(bool, str, object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            payload = self.fn()
            self.done.emit(True, "연결 성공", payload)
        except Exception as e:
            self.done.emit(False, str(e), None)


SETTINGS_QSS_TEMPLATE = """
    * { font-family: $FONT_STACK; }
    QDialog, QWidget { background: $BG; color: $TEXT; }
    QTabWidget::pane { border: 1px solid $BORDER; background: $SURFACE; border-radius: $RADIUS_SM; }
    QTabBar::tab { background: $SURFACE_RAISED; color: $TEXT_DIM; padding: 10px 18px; border: 1px solid $BORDER; border-bottom: none; }
    QTabBar::tab:hover { color: $TEXT; background: $SURFACE_HOVER; }
    QTabBar::tab:selected { background: $ACCENT_SOFT; color: $TEXT; border-color: $ACCENT_SOFT_BORDER; }
    QGroupBox { background: $SURFACE; border: 1px solid $BORDER; border-radius: 10px; margin-top: 12px; padding-top: 12px; }
    QGroupBox::title { color: $TEXT_MUTED; padding: 0 8px; }
    QLabel { color: $TEXT_MUTED; }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QListWidget { background: $SURFACE_INPUT; color: $TEXT; border: 1px solid $BORDER_STRONG; border-radius: 7px; padding: 7px; }
    QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QPlainTextEdit:hover, QListWidget:hover { border-color: $BORDER_HOVER; }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: $ACCENT; }
    QListWidget::item { padding: 8px 6px; border-radius: 6px; color: $TEXT_MUTED; }
    QListWidget::item:hover { background: $SURFACE_RAISED; color: $TEXT; }
    QListWidget::item:selected { background: $ACCENT_SOFT; color: $TEXT; }
    QPushButton { background: $SURFACE_RAISED; color: $TEXT; border: 1px solid $BORDER_STRONG; border-radius: $RADIUS_SM; padding: 8px 14px; font-weight: 600; }
    QPushButton:hover { background: $SURFACE_HOVER; border-color: $BORDER_HOVER; }
    QPushButton:pressed { background: $SURFACE_INPUT; border-color: $BORDER_STRONG; }
    QPushButton:disabled { color: $TEXT_FAINT; background: $BG; border-color: $BORDER; }
    QPushButton#applyButton { background: $ACCENT; color: $ACCENT_INK; border: none; font-weight: 800; }
    QPushButton#applyButton:hover { background: $ACCENT_HOVER; }
    QPushButton#applyButton:pressed { background: $ACCENT_PRESSED; }
    QCheckBox { color: $TEXT_MUTED; }
    QScrollBar:vertical { background: transparent; width: 10px; margin: 3px 2px; }
    QScrollBar::handle:vertical { background: $BORDER_STRONG; min-height: 30px; border-radius: 4px; }
    QScrollBar::handle:vertical:hover { background: $BORDER_HOVER; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; background: transparent; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


class SettingsWindow:
    """Qt Designer UI를 독립 QDialog로 열고, Apply 때만 설정을 반영한다."""

    def __init__(self, manager, lm_factory, comfy_factory, parent=None):
        self.manager = manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.worker = None
        self.ai_worker = None
        self.image_models = ImageModelManager(manager)
        self._loading_model = False
        self.parent_widget = parent

        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent.parent / "ui" / "settings_window.ui"
        self.form = loader.load(str(ui_path), parent)
        if self.form is None or not isinstance(self.form, QDialog):
            raise RuntimeError(f"settings_window.ui를 QDialog로 로드할 수 없습니다: {ui_path}")

        self.form.setStyleSheet(theme.render(SETTINGS_QSS_TEMPLATE))

        self._setup_font_combo()
        self.aiWorkflowButton = self.form.aiWorkflowButton
        self.workflowStatusLabel = self.form.workflowStatusLabel
        self.workflowStatusLabel.setWordWrap(True)

        self._load()
        self.form.applyButton.clicked.connect(self.apply)
        self.form.cancelButton.clicked.connect(self.form.reject)
        self.form.lmTestButton.clicked.connect(self.test_lm)
        self.form.comfyTestButton.clicked.connect(self.test_comfy)
        self.form.browseWorkflowButton.clicked.connect(self.browse_workflow)

        self.form.imageModelList.currentRowChanged.connect(self._model_row_changed)
        self.form.addImageModelButton.clicked.connect(self.add_image_model)
        self.form.removeImageModelButton.clicked.connect(self.remove_image_model)
        self.form.saveImageModelButton.clicked.connect(self.save_image_model)
        self.form.browseImageModelButton.clicked.connect(self.browse_image_model)
        self.form.browseImageModelWorkflowButton.clicked.connect(self.browse_image_model_workflow)
        self.aiWorkflowButton.clicked.connect(self.generate_workflow_with_ai)

    def _setup_font_combo(self):
        label = QLabel("UI 폰트", self.form)
        combo = QComboBox(self.form)
        combo.setObjectName("uiFontCombo")
        combo.addItem("시스템 기본")
        families = [f for f in theme._system_font_families() if f != "시스템 기본"]
        if len(families) > 400:
            families = families[:400]
        combo.addItems(families)
        combo.setToolTip("앱 전체에 쓰는 UI 폰트를 고른다. 고르는 즉시 설정창에 미리보기된다.")
        self.form.generalForm.addRow(label, combo)
        self.uiFontLabel = label
        self.uiFontCombo = combo
        combo.currentTextChanged.connect(self._preview_font)

    def _preview_font(self):
        theme.apply_font(self._current_font_family())
        theme.load_fonts()
        self.form.setStyleSheet(theme.render(SETTINGS_QSS_TEMPLATE))

    def _current_font_family(self):
        combo = getattr(self, "uiFontCombo", None)
        if combo is None:
            return None
        text = combo.currentText().strip()
        return None if text == "시스템 기본" else text

    def _load(self):
        lm = self.manager.section("lmstudio")
        cf = self.manager.section("comfyui")
        g = self.manager.section("general")
        from studio.services.bubble import find_font_path
        if not cf.get("font_path"):
            cf["font_path"] = find_font_path("")
        self.form.lmHostEdit.setText(str(lm.get("host", "127.0.0.1")))
        self.form.lmPortSpin.setValue(int(lm.get("port", 1234)))
        self.form.lmApiEdit.setText(str(lm.get("api_path", "/v1")))
        saved_model = str(lm.get("model", ""))
        if saved_model:
            self.form.lmModelCombo.addItem(saved_model)
        self.form.lmModelCombo.setCurrentText(saved_model)
        self.form.lmStatusLabel.setText("상태: 연결 확인 필요")
        self.form.comfyHostEdit.setText(str(cf.get("host", "127.0.0.1")))
        self.form.comfyPortSpin.setValue(int(cf.get("port", 8188)))
        self.form.comfyWorkflowEdit.setText(str(cf.get("workflow", "resources/4cut_default.json")))
        self.form.comfyStatusLabel.setText("상태: 연결 확인 필요")
        self.form.projectPathEdit.setText(str(g.get("project_path", "projects")))
        self.form.widthSpin.setValue(int(g.get("width", 512)))
        self.form.heightSpin.setValue(int(g.get("height", 512)))
        self.form.autoSaveCheck.setChecked(bool(g.get("auto_save", True)))
        stored = g.get("ui_font_family")
        if stored:
            idx = self.uiFontCombo.findText(str(stored))
            if idx >= 0:
                self.uiFontCombo.setCurrentIndex(idx)

        self.form.imageModelSamplerCombo.addItems([
            "euler_ancestral", "euler", "dpmpp_2m", "dpmpp_2m_sde", "ddim", "uni_pc"
        ])
        self.form.imageModelSchedulerCombo.addItems([
            "beta", "normal", "sgm_uniform", "simple", "karras", "exponential"
        ])
        self._refresh_model_list(self.image_models.selected_id())

    def _capture(self):
        return {
            "lmstudio": {
                "host": self.form.lmHostEdit.text().strip(),
                "port": self.form.lmPortSpin.value(),
                "api_path": self.form.lmApiEdit.text().strip() or "/v1",
                "model": self.form.lmModelCombo.currentText().strip(),
            },
            "comfyui": {
                "host": self.form.comfyHostEdit.text().strip(),
                "port": self.form.comfyPortSpin.value(),
                "workflow": self.form.comfyWorkflowEdit.text().strip(),
            },
            "general": {
                "project_path": self.form.projectPathEdit.text().strip() or "projects",
                "ui_font_family": self._current_font_family(),
                "width": self.form.widthSpin.value(),
                "height": self.form.heightSpin.value(),
                "auto_save": self.form.autoSaveCheck.isChecked(),
            },
        }

    def test_lm(self):
        if self.worker is not None and self.worker.isRunning():
            return
        values = self._capture()["lmstudio"]
        self.form.lmStatusLabel.setText("상태: 연결 테스트 중...")
        self.form.lmTestButton.setEnabled(False)
        self.worker = ConnectionWorker(lambda: self.lm_factory(values).list_models(), self.form)
        self.worker.done.connect(self._lm_test_done)
        self.worker.start()

    def test_comfy(self):
        if self.worker is not None and self.worker.isRunning():
            return
        values = self._capture()["comfyui"]
        self.form.comfyStatusLabel.setText("상태: 연결 테스트 중...")
        self.form.comfyTestButton.setEnabled(False)
        self.worker = ConnectionWorker(lambda: self.comfy_factory(values).test_connection(), self.form)
        self.worker.done.connect(lambda ok, msg, _payload: self._test_done(self.form.comfyStatusLabel, self.form.comfyTestButton, ok, msg))
        self.worker.start()

    def _test_done(self, label, button, ok, msg):
        label.setText(("상태: ✓ " if ok else "상태: ✗ ") + msg)
        button.setEnabled(True)

    def _lm_test_done(self, ok, msg, models):
        self._test_done(self.form.lmStatusLabel, self.form.lmTestButton, ok, msg)
        if not ok:
            return
        ids = [str(m) for m in (models or []) if str(m).strip()]
        combo = self.form.lmModelCombo
        current = combo.currentText().strip()
        combo.clear()
        combo.addItems(ids)
        if current in ids:
            combo.setCurrentText(current)
        elif ids:
            combo.setCurrentIndex(0)
        combo.setToolTip("\n".join(ids))
        if ids:
            self.form.lmStatusLabel.setText(f"상태: ✓ {msg} · 모델 {len(ids)}개")
        else:
            self.form.lmStatusLabel.setText(f"상태: ✓ {msg} (모델 없음)")

    def browse_workflow(self):
        path, _ = QFileDialog.getOpenFileName(self.form, "ComfyUI Workflow 선택", "", "JSON (*.json)")
        if path:
            self.form.comfyWorkflowEdit.setText(path)

    # ----- Image model manager -----
    def _refresh_model_list(self, selected_id=None):
        self._loading_model = True
        try:
            self.form.imageModelList.clear()
            profiles = self.image_models.profiles()
            target = selected_id or self.image_models.selected_id()
            row = 0
            for i, profile in enumerate(profiles):
                item = QListWidgetItem(profile.name)
                item.setData(32, profile.id)
                self.form.imageModelList.addItem(item)
                if profile.id == target:
                    row = i
            if profiles:
                self.form.imageModelList.setCurrentRow(row)
        finally:
            self._loading_model = False
        self._load_model_row(self.form.imageModelList.currentRow())

    def _model_row_changed(self, row):
        if not self._loading_model:
            profiles = self.image_models.profiles()
            if 0 <= row < len(profiles):
                self.image_models.select(profiles[row].id)
            self._load_model_row(row)

    def _load_model_row(self, row):
        profiles = self.image_models.profiles()
        if row < 0 or row >= len(profiles):
            return
        profile = profiles[row]
        self._loading_model = True
        try:
            self.form.imageModelNameEdit.setText(profile.name)
            self.form.imageModelFileEdit.setText(profile.model_file)
            self.form.imageModelWorkflowEdit.setText(profile.workflow)
            self.form.imageModelWidthSpin.setValue(profile.width)
            self.form.imageModelHeightSpin.setValue(profile.height)
            self.form.imageModelStepsSpin.setValue(profile.steps)
            self.form.imageModelCfgSpin.setValue(profile.cfg)
            self.form.imageModelSamplerCombo.setCurrentText(profile.sampler)
            self.form.imageModelSchedulerCombo.setCurrentText(profile.scheduler)
            self.form.imageModelNegativeEdit.setPlainText(profile.negative_prompt)
        finally:
            self._loading_model = False
        self._update_workflow_status(profile)

    def _form_profile(self):
        row = self.form.imageModelList.currentRow()
        profiles = self.image_models.profiles()
        old_profile = profiles[row] if 0 <= row < len(profiles) else None
        old_id = old_profile.id if old_profile else ""
        return ImageModelProfile(
            id=old_id,
            name=self.form.imageModelNameEdit.text().strip() or "Custom Model",
            model_file=self.form.imageModelFileEdit.text().strip(),
            workflow=self.form.imageModelWorkflowEdit.text().strip(),
            # 설정 UI에서 수동 지정하지 않으므로 기존 설정값을 보존한다.
            stage2_workflow=old_profile.stage2_workflow if old_profile else "",
            width=self.form.imageModelWidthSpin.value(),
            height=self.form.imageModelHeightSpin.value(),
            steps=self.form.imageModelStepsSpin.value(),
            cfg=self.form.imageModelCfgSpin.value(),
            sampler=self.form.imageModelSamplerCombo.currentText().strip() or "euler_ancestral",
            scheduler=self.form.imageModelSchedulerCombo.currentText().strip() or "normal",
            negative_prompt=self.form.imageModelNegativeEdit.toPlainText().strip(),
        )

    # ----- workflow automation -----
    def _resources_dir(self):
        """워크플로우·config가 함께 사는 폴더(기본 resources/)."""
        return Path(self.manager.path).parent

    def _resolve_workflow(self, value):
        if not str(value or "").strip():
            return None
        return Path(self.manager.resolve_path(value))

    def _display_workflow_path(self, path):
        return workflow_factory.to_config_path(path, self.manager.base_dir)

    def _set_workflow_status(self, text, ok=None):
        colors = {True: theme.SUCCESS_TEXT, False: theme.DANGER_TEXT, None: theme.TEXT_MUTED}
        self.workflowStatusLabel.setText(text)
        self.workflowStatusLabel.setStyleSheet(f"color: {colors.get(ok, theme.TEXT_MUTED)};")

    def _comfy_client(self):
        return self.comfy_factory({
            "host": self.form.comfyHostEdit.text().strip() or "127.0.0.1",
            "port": self.form.comfyPortSpin.value(),
        })

    def _current_model_context(self):
        """현재 폼에서 (프로필, 모델 id, 모델 파일명) 을 뽑는다."""
        row = self.form.imageModelList.currentRow()
        profiles = self.image_models.profiles()
        profile = profiles[row] if 0 <= row < len(profiles) else None
        model_file = self.form.imageModelFileEdit.text().strip()
        model_id = profile.id if profile is not None else workflow_factory.slugify(model_file)
        return profile, model_id, model_file

    def _update_workflow_status(self, profile):
        """리스트에서 모델을 고를 때는 구조 검사만 빠르게 보여준다(네트워크 호출 없음)."""
        if not profile.model_file:
            self._set_workflow_status("모델 파일을 선택하면 워크플로우가 자동 생성됩니다.", ok=None)
            return
        if not profile.workflow:
            self._set_workflow_status("워크플로우가 없습니다 — 모델 파일을 다시 선택하면 자동 생성합니다.", ok=None)
            return
        self._report_workflow(profile.workflow, profile.model_file, check_comfy=False)

    def _report_workflow(self, workflow_value, model_file, check_comfy=True):
        """워크플로우 구조 검사(+선택적 ComfyUI 보유 확인) 후 결과를 상태 라벨에 보여준다."""
        path = self._resolve_workflow(workflow_value)
        if path is None:
            self._set_workflow_status("⚠ 워크플로우가 지정되지 않았습니다.", ok=False)
            return False
        errors = workflow_factory.validate_workflow(path, model_file=model_file)
        if not errors:
            profile, _, _ = self._current_model_context()
            if profile is not None and profile.model_file == model_file:
                errors = workflow_factory.validate_runnable(path, profile)
        if errors:
            self._set_workflow_status("⚠ 호환성 검사 실패 — " + " / ".join(errors), ok=False)
            return False
        if not check_comfy:
            self._set_workflow_status("✓ 워크플로우 검사 통과 — 저장할 때 ComfyUI 보유 여부까지 확인합니다.", ok=True)
            return True
        status, detail = workflow_factory.check_model_file(self._comfy_client(), model_file)
        if status == "missing":
            self._set_workflow_status("⚠ " + detail, ok=False)
            return False
        if status == "ok":
            self._set_workflow_status("✓ 사용 준비 완료 — " + detail, ok=True)
        else:
            self._set_workflow_status("✓ 워크플로우 검사 통과 · " + detail, ok=None)
        return True

    def _autocreate_workflow(self, model_file):
        """모델 파일만 골랐을 때 기본 템플릿으로 워크플로우를 만들어 준다."""
        if not model_file:
            return None
        current = self.form.imageModelWorkflowEdit.text().strip()
        existing = self._resolve_workflow(current)
        if existing is not None and existing.is_file():
            self._report_workflow(current, model_file)
            return current
        _, model_id, _ = self._current_model_context()
        try:
            path = workflow_factory.build_from_template(model_file, model_id, self._resources_dir())
        except Exception as e:
            self._set_workflow_status(f"⚠ 워크플로우 자동 생성 실패: {e}", ok=False)
            return None
        value = self._display_workflow_path(path)
        self.form.imageModelWorkflowEdit.setText(value)
        self._report_workflow(value, model_file)
        return value

    def generate_workflow_with_ai(self):
        """LM Studio로 워크플로우 생성을 시도하고, 검증을 통과한 결과만 적용한다(실험적)."""
        _, model_id, model_file = self._current_model_context()
        if not model_file:
            self._set_workflow_status("⚠ 모델 파일을 먼저 선택하세요.", ok=False)
            return
        lm_settings = dict(self.manager.section("lmstudio"))
        if not str(lm_settings.get("model", "")).strip():
            self._set_workflow_status("⚠ LM Studio 모델이 설정되지 않아 AI 생성을 쓸 수 없습니다. AI 서버 탭에서 모델을 고르세요.", ok=False)
            return
        if self.ai_worker is not None and self.ai_worker.isRunning():
            return
        resources_dir = self._resources_dir()
        template_name = Path(self.form.comfyWorkflowEdit.text().strip() or workflow_factory.TEMPLATE_FILENAME).name
        if not (resources_dir / template_name).is_file():
            template_name = workflow_factory.TEMPLATE_FILENAME
        lm_client = self.lm_factory(lm_settings)
        self.aiWorkflowButton.setEnabled(False)
        self._set_workflow_status("AI가 워크플로우를 만드는 중입니다…", ok=None)
        self.ai_worker = ConnectionWorker(
            lambda: workflow_factory.generate_with_llm(
                lm_client, model_file, resources_dir, model_id, template_name=template_name
            ),
            self.form,
        )
        self.ai_worker.done.connect(self._ai_workflow_done)
        self.ai_worker.start()

    def _ai_workflow_done(self, ok, message, payload):
        self.aiWorkflowButton.setEnabled(True)
        self.ai_worker = None
        if not ok or payload is None:
            self._set_workflow_status(f"⚠ AI 생성 실패 — 기존 워크플로우를 유지합니다: {message}", ok=False)
            return
        self.form.imageModelWorkflowEdit.setText(self._display_workflow_path(payload))
        self._report_workflow(payload, self.form.imageModelFileEdit.text().strip())

    def save_image_model(self):
        profile = self._form_profile()
        if not profile.model_file:
            self._set_workflow_status("⚠ 모델 파일을 먼저 선택하세요.", ok=False)
            return
        if not profile.workflow:
            self._autocreate_workflow(profile.model_file)
            profile.workflow = self.form.imageModelWorkflowEdit.text().strip()
        path = self._resolve_workflow(profile.workflow)
        errors = workflow_factory.validate_workflow(path, model_file=profile.model_file) if path else ["워크플로우가 지정되지 않았습니다."]
        if not errors:
            errors = workflow_factory.validate_runnable(path, profile)
        if errors:
            QMessageBox.warning(
                self.form,
                "워크플로우 확인 필요",
                "모델 정보를 저장할 수 없습니다.\n\n- " + "\n- ".join(errors)
                + "\n\n'AI로 워크플로우 만들기 (실험적)'를 시도하거나, 워크플로우 파일을 직접 지정해 주세요.",
            )
            self._set_workflow_status("⚠ " + errors[0], ok=False)
            return
        saved = self.image_models.upsert(profile)
        self.image_models.save()
        self._refresh_model_list(saved.id)
        self._report_workflow(profile.workflow, profile.model_file)

    def add_image_model(self):
        existing_ids = {p.id for p in self.image_models.profiles()}
        model_id = "custom_model"
        index = 2
        while model_id in existing_ids:
            model_id = f"custom_model_{index}"
            index += 1
        profile = ImageModelProfile(
            id=model_id,
            name="새 이미지 모델",
            model_file="",
            workflow="",
            width=self.form.widthSpin.value(),
            height=self.form.heightSpin.value(),
            steps=28,
            cfg=4.0,
            sampler="euler_ancestral",
            scheduler="normal",
            negative_prompt="low quality, blurry, deformed",
        )
        saved = self.image_models.upsert(profile)
        self.image_models.save()
        self._refresh_model_list(saved.id)
        self._set_workflow_status("모델 파일을 선택하면 워크플로우가 자동 생성됩니다.", ok=None)

    def remove_image_model(self):
        row = self.form.imageModelList.currentRow()
        profiles = self.image_models.profiles()
        if row < 0 or row >= len(profiles) or len(profiles) <= 1:
            return
        model_id = profiles[row].id
        self.image_models.remove(model_id)
        self.image_models.save()
        self._refresh_model_list(self.image_models.selected_id())

    def browse_image_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self.form, "ComfyUI 이미지 모델 선택", "", "Model (*.safetensors *.gguf);;All Files (*)"
        )
        if not path:
            return
        model_file = Path(path).name
        self.form.imageModelFileEdit.setText(model_file)
        # 워크플로우를 몰라도 되도록, 모델 파일만 고르면 기본 템플릿으로 자동 생성한다.
        self._autocreate_workflow(model_file)

    def browse_image_model_workflow(self):
        path, _ = QFileDialog.getOpenFileName(self.form, "이미지 모델 Workflow 선택", "", "JSON (*.json)")
        if path:
            self.form.imageModelWorkflowEdit.setText(path)

    def apply(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)
        # Persist the currently edited image model as part of Apply.
        if self.form.imageModelList.currentRow() >= 0:
            profile = self._form_profile()
            if profile.model_file and profile.workflow:
                self.image_models.upsert(profile)
        values = self._capture()
        # 섹션 전체를 덮어쓰지 않고 병합한다. (폼에 없는 키 보존: font_path 등)
        for section, section_values in values.items():
            self.manager.data.setdefault(section, {}).update(section_values)
        self.image_models.save()
        self.manager.save()
        theme.apply_font(self._current_font_family())
        theme.load_fonts()
        main = getattr(self, "parent_widget", None)
        if main is not None and hasattr(main, "reload_theme"):
            main.reload_theme()
        self.form.accept()

    def exec(self):
        return self.form.exec()
