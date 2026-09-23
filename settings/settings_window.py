from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QFileDialog, QListWidgetItem
from settings.model_manager import ImageModelManager
from core.models.image_model import ImageModelProfile
from ui import theme


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
        self.image_models = ImageModelManager(manager)
        self._loading_model = False

        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent.parent / "ui" / "settings" / "settings_window.ui"
        self.form = loader.load(str(ui_path), parent)
        if self.form is None or not isinstance(self.form, QDialog):
            raise RuntimeError(f"settings_window.ui를 QDialog로 로드할 수 없습니다: {ui_path}")

        self.form.setStyleSheet(theme.render(SETTINGS_QSS_TEMPLATE))

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

    def _load(self):
        lm = self.manager.section("lmstudio")
        cf = self.manager.section("comfyui")
        g = self.manager.section("general")
        from compose.bubble import find_font_path
        if not cf.get("font_path"):
            cf["font_path"] = find_font_path("")
        if not cf.get("font_size"):
            cf["font_size"] = 32
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
        self.form.comfyWorkflowEdit.setText(str(cf.get("workflow", "workflows/4cut_default.json")))
        self.form.comfyStatusLabel.setText("상태: 연결 확인 필요")
        self.form.projectPathEdit.setText(str(g.get("project_path", "projects")))
        self.form.widthSpin.setValue(int(g.get("width", 768)))
        self.form.heightSpin.setValue(int(g.get("height", 768)))
        self.form.autoSaveCheck.setChecked(bool(g.get("auto_save", True)))

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

    def _form_profile(self):
        row = self.form.imageModelList.currentRow()
        profiles = self.image_models.profiles()
        old_id = profiles[row].id if 0 <= row < len(profiles) else ""
        return ImageModelProfile(
            id=old_id,
            name=self.form.imageModelNameEdit.text().strip() or "Custom Model",
            model_file=self.form.imageModelFileEdit.text().strip(),
            workflow=self.form.imageModelWorkflowEdit.text().strip(),
            width=self.form.imageModelWidthSpin.value(),
            height=self.form.imageModelHeightSpin.value(),
            steps=self.form.imageModelStepsSpin.value(),
            cfg=self.form.imageModelCfgSpin.value(),
            sampler=self.form.imageModelSamplerCombo.currentText().strip() or "euler_ancestral",
            scheduler=self.form.imageModelSchedulerCombo.currentText().strip() or "normal",
            negative_prompt=self.form.imageModelNegativeEdit.toPlainText().strip(),
        )

    def save_image_model(self):
        profile = self._form_profile()
        if not profile.model_file:
            return
        saved = self.image_models.upsert(profile)
        self.image_models.save()
        self._refresh_model_list(saved.id)

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
        if path:
            self.form.imageModelFileEdit.setText(Path(path).name)

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
        self.form.accept()

    def exec(self):
        return self.form.exec()
