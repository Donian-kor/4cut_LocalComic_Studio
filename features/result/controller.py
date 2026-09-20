class ResultController:
    def __init__(self, widget):
        self.widget = widget

    def show_result(self, comic):
        self.widget.show_result(comic)
