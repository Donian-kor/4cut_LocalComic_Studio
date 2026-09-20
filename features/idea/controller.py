class IdeaController:
    def __init__(self, widget, on_generate):
        self.widget = widget
        self.on_generate = on_generate
        widget.generateRequested.connect(self._generate)

    def _generate(self, idea, style):
        idea = idea.strip()
        if idea:
            self.on_generate(idea, style)
