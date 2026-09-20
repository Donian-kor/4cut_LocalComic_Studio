from PySide6.QtCore import QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QFileDialog

class ConnectionWorker(QThread):
    done = Signal(bool, str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.fn()
            self.done.emit(True, "연결 성공")
        except Exception as e:
            self.done.emit(False, str(e))

class SettingsWindow(QDialog):
    def __init__(self, manager, lm_factory, comfy_factory, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        loader = QUiLoader()
        self.form = loader.load("ui/settings/settings_window.ui", None)
        self.setLayout(self.form.layout())
        self.worker = None
        self._load()
        self.form.applyButton.clicked.connect(self.apply)
        self.form.cancelButton.clicked.connect(self.reject)
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
        self.form.lmModelEdit.setText(str(lm.get("model", "")))
        self.form.comfyHostEdit.setText(str(cf.get("host", "127.0.0.1")))
        self.form.comfyPortSpin.setValue(int(cf.get("port", 8188)))
        self.form.comfyWorkflowEdit.setText(str(cf.get("workflow", "workflows/4cut_default.json")))
        self.form.projectPathEdit.setText(str(g.get("project_path", "projects")))
        self.form.widthSpin.setValue(int(g.get("width", 768)))
        self.form.heightSpin.setValue(int(g.get("height", 768)))
        self.form.autoSaveCheck.setChecked(bool(g.get("auto_save", True)))

    def _capture(self):
        self.manager.section("lmstudio").update({
            "host": self.form.lmHostEdit.text().strip(),
            "port": self.form.lmPortSpin.value(),
            "api_path": self.form.lmApiEdit.text().strip(),
            "model": self.form.lmModelEdit.text().strip()
        })
        self.manager.section("comfyui").update({
            "host": self.form.comfyHostEdit.text().strip(),
            "port": self.form.comfyPortSpin.value(),
            "workflow": self.form.comfyWorkflowEdit.text().strip()
        })
        self.manager.section("general").update({
            "project_path": self.form.projectPathEdit.text().strip(),
            "width": self.form.widthSpin.value(),
            "height": self.form.heightSpin.value(),
            "auto_save": self.form.autoSaveCheck.isChecked()
        })

    def test_lm(self):
        self._capture()
        self.form.lmStatusLabel.setText("상태: 연결 테스트 중...")
        self.form.lmTestButton.setEnabled(False)
        self.worker = ConnectionWorker(
            lambda: self.lm_factory(self.manager.section("lmstudio")).test_connection()
        )
        self.worker.done.connect(
            lambda ok, msg: self._test_done(
                self.form.lmStatusLabel, self.form.lmTestButton, ok, msg
            )
        )
        self.worker.start()

    def test_comfy(self):
        self._capture()
        self.form.comfyStatusLabel.setText("상태: 연결 테스트 중...")
        self.form.comfyTestButton.setEnabled(False)
        self.worker = ConnectionWorker(
            lambda: self.comfy_factory(self.manager.section("comfyui")).test_connection()
        )
        self.worker.done.connect(
            lambda ok, msg: self._test_done(
                self.form.comfyStatusLabel, self.form.comfyTestButton, ok, msg
            )
        )
        self.worker.start()

    def _test_done(self, label, button, ok, msg):
        label.setText(("상태: ✓ " if ok else "상태: ✗ ") + msg)
        button.setEnabled(True)

    def browse_workflow(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "ComfyUI Workflow 선택", "", "JSON (*.json)"
        )
        if path:
            self.form.comfyWorkflowEdit.setText(path)

    def apply(self):
        self._capture()
        self.manager.save()
        self.accept()
