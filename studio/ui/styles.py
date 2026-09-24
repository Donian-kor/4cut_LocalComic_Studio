from pathlib import Path


QSS_PATH = Path(__file__).with_name("main_window.qss")
MAIN_WINDOW_QSS_TEMPLATE = QSS_PATH.read_text(encoding="utf-8")
