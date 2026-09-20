class PreviewController:
    def __init__(self, widget):
        self.widget = widget

    def show_comic(self, comic):
        self.widget.show_comic(comic)
