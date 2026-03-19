import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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

    def get_render_param(self, key: str, default: Any = None) -> Any:
        """Resolve rendering parameter from direct params first, then render_profile."""
        if key in self.parameters:
            return self.parameters.get(key)
        render_profile = self.parameters.get("render_profile", {})
        if isinstance(render_profile, dict):
            return render_profile.get(key, default)
        return default

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
        header = (
            f"from manim import *\n"
            f"import numpy as np\n\n"
            f"config.background_color = '{self.background_color}'\n"
        )

        frame_rate = self.get_render_param("frame_rate")
        if frame_rate is not None:
            try:
                frame_rate_int = int(float(frame_rate))
                if frame_rate_int > 0:
                    header += f"config.frame_rate = {frame_rate_int}\n"
            except (TypeError, ValueError):
                pass

        header += "\n"
        return header

    def get_class_def(self, base_class: str = "Scene") -> str:
        return f"class {self.scene_name}({base_class}):\n    def construct(self):\n"
