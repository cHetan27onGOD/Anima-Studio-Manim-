from typing import Any, Dict
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, CompositionContext

class DrawCurveTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        expr = self.parameters.get("expression", "x**2")
        color = self.parameters.get("color", "BLUE")
        obj_id = self.parameters.get("object_id", "curve")
        x_range = self.parameters.get("x_range", [-5, 5])
        y_range = self.parameters.get("y_range", [-3, 3])
        
        # Ensure ranges are lists (avoid type mismatch)
        if isinstance(x_range, str): x_range = eval(x_range)
        if isinstance(y_range, str): y_range = eval(y_range)
        
        if not context.object_exists("axes"):
            context.add_obj("axes", "axes", f"        ax = Axes(x_range={x_range}, y_range={y_range}, axis_config={{'include_tip': True}})\n")
        context.add_obj(obj_id, "curve", f"        {obj_id} = ax.plot(lambda x: {expr}, color={color})\n")
        label_text = self.parameters.get("label")
        if label_text:
            context.add_obj(f"{obj_id}_label", "label", f"        {obj_id}_label = MathTex(r'{label_text}', color={color}).next_to({obj_id}, UP)\n")
            context.add_anim(f"        self.play(Create({obj_id}), Write({obj_id}_label))\n")
        else:
            context.add_anim(f"        self.play(Create({obj_id}))\n")

class PlacePointTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        if not context.object_exists("axes"):
            context.add_obj("axes", "axes", "        ax = Axes()\n")
        x_val = self.parameters.get("x", 0)
        # Ensure x_val is a float (avoid type mismatch)
        try: x_val = float(x_val)
        except: x_val = 0
        y_expr = self.parameters.get("y_expression", f"{x_val}**2")
        color = self.parameters.get("color", "YELLOW")
        context.add_obj("point", "dot", f"        point = Dot(ax.c2p({x_val}, {y_expr}), color={color})\n")
        context.add_anim("        self.play(FadeIn(point))\n")

class DrawArrowTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        start = self.parameters.get("start", [0, 0, 0])
        end = self.parameters.get("end", [1, 1, 0])
        if isinstance(start, str): start = eval(start)
        if isinstance(end, str): end = eval(end)
        color = self.parameters.get("color", "GOLD")
        context.add_obj("arrow", "arrow", f"        arrow = Arrow({start}, {end}, color={color})\n")
        context.add_anim("        self.play(GrowArrow(arrow))\n")

class DrawAxisTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        if context.object_exists("axes"): return
        x_range = self.parameters.get("x_range", [-5, 5])
        y_range = self.parameters.get("y_range", [-3, 3])
        if isinstance(x_range, str): x_range = eval(x_range)
        if isinstance(y_range, str): y_range = eval(y_range)
        context.add_obj("axes", "axes", f"        ax = Axes(x_range={x_range}, y_range={y_range}, axis_config={{'include_tip': True}})\n")
        context.add_anim("        self.play(Create(ax))\n")

class WriteTextTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        text = self.parameters.get("text", "Hello")
        pos = self.parameters.get("position", "UP")
        context.add_obj("text", "text", f"        txt = Text('{text}', font_size=32).to_edge({pos})\n")
        context.add_anim("        self.play(Write(txt))\n")

class CreateVectorTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        if not context.object_exists("axes"):
            context.add_obj("axes", "axes", "        ax = Axes()\n")
        coords = self.parameters.get("coords", [1, 1, 0])
        color = self.parameters.get("color", "YELLOW")
        context.add_obj("vector", "vector", f"        vec = Vector({coords}, color={color})\n")
        context.add_anim("        self.play(GrowArrow(vec))\n")

class TransformObjectTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        src = self.parameters.get("source_id", "obj1")
        tgt = self.parameters.get("target_id", "obj2")
        context.add_anim(f"        self.play(ReplacementTransform({src}, {tgt}))\n")

class HighlightObjectTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        oid = self.parameters.get("target_id", "obj")
        context.add_anim(f"        self.play(Indicate({oid}))\n")
