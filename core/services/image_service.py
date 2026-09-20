from pathlib import Path

class ImageService:
    def __init__(self, comfy_client, workflow_adapter, width=768, height=768):
        self.comfy = comfy_client
        self.workflow = workflow_adapter
        self.width = width
        self.height = height

    def generate_panel(self, panel, output_dir):
        workflow = self.workflow.prepare(panel.image_prompt, panel.seed, self.width, self.height)
        prompt_id = self.comfy.queue_prompt(workflow)
        data = self.comfy.wait_for_image(prompt_id)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"panel_{panel.index}.png"
        path.write_bytes(data)
        panel.image_path = str(path)
        return str(path)
