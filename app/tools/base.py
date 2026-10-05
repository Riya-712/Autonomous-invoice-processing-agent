from typing import Any, Callable
from app.models.tool_result import ToolResult

class Tool:
    def __init__(self, name: str, description: str, schema: dict[str, Any], handler: Callable[..., ToolResult]):
        self.name = name
        self.description = description
        self.schema = schema
        self.handler = handler

    def openai_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema,
            },
        }
