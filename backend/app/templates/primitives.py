from typing import Any, Dict
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate

class DrawCurveTemplate(CompositionAwareTemplate):
    """Micro-template to draw a mathematical curve."""
    def compose(self) -> None:
        expr = self.parameters.get("expression", "x**2")
        color = self.parameters.get("color", "BLUE")
        
        # Create axes
        axes_code = "        ax = Axes()\n"
        self.create_object("axes", "axes", axes_code, {"expression": expr})
        
        # Create curve
        curve_code = f"        curve = ax.plot(lambda x: {expr}, color={color})\n"
        self.create_object("curve", "curve", curve_code, {"expression": expr, "color": color})
        
        # Animate creation
        anim_code = "        self.play(Create(ax), Create(curve))\n"
        self.add_animation_code(anim_code)

class PlacePointTemplate(CompositionAwareTemplate):
    """Micro-template to place a point on a curve."""
    def compose(self) -> None:
        available = self.get_available_objects()
        
        # Use existing axes/curve or create them
        if "axes" not in available:
            axes_code = "        ax = Axes()\n"
            self.create_object("axes", "axes", axes_code)
        
        x_val = self.parameters.get("x", 0)
        y_expr = self.parameters.get("y_expression", f"{x_val}**2")
        color = self.parameters.get("color", "YELLOW")
        
        # Create point
        point_code = f"        point = Dot(ax.c2p({x_val}, {y_expr}), color={color})\n"
        self.create_object("point", "dot", point_code, {"x": x_val, "color": color})
        
        # Animate appearance
        anim_code = "        self.play(FadeIn(point))\n"
        self.add_animation_code(anim_code)

class DrawArrowTemplate(CompositionAwareTemplate):
    """Micro-template to draw an arrow indicator."""
    def compose(self) -> None:
        start = self.parameters.get("start", [0, 0, 0])
        end = self.parameters.get("end", [1, 1, 0])
        color = self.parameters.get("color", "GOLD")
        
        arrow_code = f"        arrow = Arrow({start}, {end}, color={color})\n"
        self.create_object("arrow", "arrow", arrow_code, {"start": start, "end": end})
        
        anim_code = "        self.play(GrowArrow(arrow))\n"
        self.add_animation_code(anim_code)

class DrawAxisTemplate(CompositionAwareTemplate):
    """Micro-template to draw axes."""
    def compose(self) -> None:
        available = self.get_available_objects()
        
        # Skip if axes already created
        if "axes" in available:
            return
        
        x_range = self.parameters.get("x_range", [-5, 5])
        y_range = self.parameters.get("y_range", [-3, 3])
        
        axes_code = f"        ax = Axes(x_range={x_range}, y_range={y_range}, axis_config={{'include_tip': True}})\n"
        self.create_object("axes", "axes", axes_code, {"x_range": x_range, "y_range": y_range})
        
        anim_code = "        self.play(Create(ax))\n"
        self.add_animation_code(anim_code)

class WriteTextTemplate(CompositionAwareTemplate):
    """Micro-template to write text."""
    def compose(self) -> None:
        text = self.parameters.get("text", "Hello")
        pos = self.parameters.get("position", "UP")
        
        text_code = f"        txt = Text('{text}', font_size=32).to_edge({pos})\n"
        self.create_object("text", "text", text_code, {"text": text, "position": pos})
        
        anim_code = "        self.play(Write(txt))\n"
        self.add_animation_code(anim_code)

class CreateVectorTemplate(CompositionAwareTemplate):
    """Micro-template to create a vector."""
    def compose(self) -> None:
        available = self.get_available_objects()
        
        if "axes" not in available:
            axes_code = "        ax = Axes()\n"
            self.create_object("axes", "axes", axes_code)
        
        coords = self.parameters.get("coords", [1, 1, 0])
        color = self.parameters.get("color", "YELLOW")
        
        vec_code = f"        vec = Vector({coords}, color={color})\n"
        self.create_object("vector", "vector", vec_code, {"coords": coords, "color": color})
        
        anim_code = "        self.play(GrowArrow(vec))\n"
        self.add_animation_code(anim_code)

class TransformObjectTemplate(CompositionAwareTemplate):
    """Micro-template to transform one object into another."""
    def compose(self) -> None:
        source_id = self.parameters.get("source_id", "obj1")
        target_id = self.parameters.get("target_id", "obj2")
        
        anim_code = f"        self.play(ReplacementTransform({source_id}, {target_id}))\n"
        self.add_animation_code(anim_code)

class HighlightObjectTemplate(CompositionAwareTemplate):
    """Micro-template to pulse/highlight an object."""
    def compose(self) -> None:
        obj_id = self.parameters.get("target_id", "obj")
        
        anim_code = f"        self.play(Indicate({obj_id}))\n"
        self.add_animation_code(anim_code)
