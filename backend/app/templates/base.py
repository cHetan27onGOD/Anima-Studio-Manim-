from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json
from app.templates.styles import get_style

class BaseTemplate(ABC):
    """Base class for all Manim animation templates."""
    
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.scene_name = "Scene1"
        
        # Apply style preset
        style_name = parameters.get("style", "3b1b")
        self.style = get_style(style_name)
        self.background_color = self.style["background_color"]

    def get_style_param(self, key: str, default: Any = None) -> Any:
        """Helper to get a style parameter, prioritizing manual template overrides."""
        return self.parameters.get(key, self.style.get(key, default))

    @abstractmethod
    def generate_construct_code(self) -> str:
        """Generate the Manim code that goes inside the construct method."""
        pass

    def generate_code(self) -> str:
        """Generate the full Manim Python code (legacy)."""
        code = self.get_header()
        code += self.get_class_def()
        code += self.generate_construct_code()
        return code

    def get_header(self) -> str:
        return f"from manim import *\nimport numpy as np\n\nconfig.background_color = '{self.background_color}'\n\n"

    def get_class_def(self, base_class: str = "Scene") -> str:
        return f"class {self.scene_name}({base_class}):\n    def construct(self):\n"
