# CLAUDE.md - Global Project Instructions & Language Policy

## CRITICAL CONSTRAINTS (STRICTLY ENFORCED)
- **Language Policy**: 
  1. You must conduct all conversations, explanations, summaries, and thoughts (inner monologues) exclusively in clear, simple Korean.
  2. Even if the user provides prompts, code, error messages, or documents in English or other languages, your internal reasoning and final response must be written in Korean.
  3. Exception: Technical terms, variable names, syntax, and raw code snippets themselves should remain in their original form, but all surrounding explanations and comments inside or outside the code block MUST be in Korean.
  4. Never switch to English or any other language under any circumstances.

- **UI Development & PySide6 Rules**:
  1. When creating or modifying user interfaces, you must preserve and adhere strictly to the XML format editable by PySide6 Qt Designer (`.ui` files).
  2. Do NOT hardcode UI layouts directly in Python strings if a `.ui` file is being used. Always maintain the structural XML so the user can open and edit it in Qt Designer.

- **Workspace & File Safety**:
  1. Never delete, modify, or access any files or contents outside the current project root directory.
  2. Absolute paths leading outside the workspace are strictly prohibited. Keep all actions fully contained within this project folder.
