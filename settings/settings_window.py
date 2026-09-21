from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QFileDialog


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


class SettingsWindow:
    """Qt Designer UI를 독립 QDialog로 열고, Apply 때만 설정을 반영한다."""

    def __init__(self, manager, lm_factory, comfy_factory, parent=None):
        self.manager = manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.worker = None

        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent.parent / "ui" / "settings" / "settings_window.ui"
        self.form = loader.load(str(ui_path), parent)
        if self.form is None or not isinstance(self.form, QDialog):
            raise RuntimeError(f"settings_window.ui를 QDialog로 로드할 수 없습니다: {ui_path}")

        self._load()
        self.form.applyButton.clicked.connect(self.apply)
        self.form.cancelButton.clicked.connect(self.form.reject)
        self.form.lmTestButton.clicked.connect(self.test_lm)
        self.form.comfyTestButton.clicked.connect(self.test_comfy)
        self.form.browseWorkflowButton.clicked.connect(self.browse_workflow)

    def _load(self):
        lm = self.manager.section("lmstudio")
        cf = self.manager.section("comfyui")
        g = self.manager.section("general")
        self.form.lmHostEdit.setText(str(lm.get("host", "127.0.0.1")))
        self.form.lmPortSpin.setValue(int(lm.get("port", 1234)))
        self.form.lmApiEdit.setText(str(lm.get("api_path", "/v1")))
        saved_model = str(lm.get("model", ""))
        if saved_model:
            self.form.lmModelCombo.addItem(saved_model)
        self.form.lmModelCombo.setCurrentText(saved_model)
        self.form.comfyHostEdit.setText(str(cf.get("host", "127.0.0.1")))
        self.form.comfyPortSpin.setValue(int(cf.get("port", 8188)))
        self.form.comfyWorkflowEdit.setText(str(cf.get("workflow", "workflows/4cut_default.json")))
        self.form.projectPathEdit.setText(str(g.get("project_path", "projects")))
        self.form.widthSpin.setValue(int(g.get("width", 768)))
        self.form.heightSpin.setValue(int(g.get("height", 768)))
        self.form.autoSaveCheck.setChecked(bool(g.get("auto_save", True)))

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
        values = self._capture()["lmstudio"]
        self.form.lmStatusLabel.setText("상태: 연결 테스트 중...")
        self.form.lmTestButton.setEnabled(False)
        self.worker = ConnectionWorker(lambda: self.lm_factory(values).list_models(), self.form)
        self.worker.done.connect(self._lm_test_done)
        self.worker.start()

    def test_comfy(self):
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
            combo.showPopup()
        else:
            self.form.lmStatusLabel.setText(f"상태: ✓ {msg} (모델 없음)")

    def browse_workflow(self):
        path, _ = QFileDialog.getOpenFileName(self.form, "ComfyUI Workflow 선택", "", "JSON (*.json)")
        if path:
            self.form.comfyWorkflowEdit.setText(path)

    def apply(self):
        values = self._capture()
        self.manager.data.update(values)
        self.manager.save()
        self.form.accept()

    def exec(self):
        return self.form.exec()
