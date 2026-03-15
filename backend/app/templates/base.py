from abc import ABC, abstractmethod
from typing import Any, Dict, List
import json

class BaseTemplate(ABC):
    """Base class for all Manim animation templates."""
    
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.scene_name = "Scene1"
        self.background_color = "#0a0a0f"

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
        return f"from manim import *\n\nconfig.background_color = '{self.background_color}'\n\n"

    def get_class_def(self, base_class: str = "Scene") -> str:
        return f"class {self.scene_name}({base_class}):\n    def construct(self):\n"
