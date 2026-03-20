from typing import Any, Dict, List
import numpy as np
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, CompositionContext

# Define constants for local use
PI = np.pi
TAU = 2 * PI

class UnitCircleTemplate(CompositionAwareTemplate):
    """Advanced 3Blue1Brown style Unit Circle animation."""
    def compose(self, context: CompositionContext) -> None:
        c_cos = self.parameters.get("color_cos", "RED")
        c_sin = self.parameters.get("color_sin", "GREEN")
        c_theta = self.parameters.get("color_theta", "YELLOW")
        rt = self.parameters.get("run_time", 10)
        
        # 1. Setup Axes and Unit Circle
        context.add_obj("axes", "axes", "        ax = Axes(x_range=[-1.5, 1.5], y_range=[-1.5, 1.5], axis_config={'include_tip': True})\n")
        context.add_obj("circle", "circle", "        circle = Circle(radius=ax.get_x_unit_size(), color=WHITE).move_to(ax.c2p(0, 0))\n")
        
        # 2. Value Tracker for Angle
        context.add_obj("t", "tracker", "        t = ValueTracker(0.001)\n") # Start slightly above 0 for labels
        
        # 3. Dynamic Components (Redrawn every frame)
        # Main Radius line
        context.add_obj("radius_line", "line", "        radius_line = always_redraw(lambda: Line(ax.c2p(0, 0), ax.c2p(np.cos(t.get_value()), np.sin(t.get_value())), color=WHITE, stroke_width=2))\n")
        
        # Cosine component (Horizontal)
        context.add_obj("cos_line", "line", f"        cos_line = always_redraw(lambda: Line(ax.c2p(0, 0), ax.c2p(np.cos(t.get_value()), 0), color={c_cos}, stroke_width=6))\n")
        
        # Sine component (Vertical)
        context.add_obj("sin_line", "line", f"        sin_line = always_redraw(lambda: Line(ax.c2p(np.cos(t.get_value()), 0), ax.c2p(np.cos(t.get_value()), np.sin(t.get_value())), color={c_sin}, stroke_width=6))\n")
        
        # Moving Dot
        context.add_obj("dot", "dot", "        dot = always_redraw(lambda: Dot(ax.c2p(np.cos(t.get_value()), np.sin(t.get_value())), color=YELLOW))\n")
        
        # Theta Arc and Label
        context.add_obj("theta_arc", "arc", f"        theta_arc = always_redraw(lambda: Arc(radius=0.3, start_angle=0, angle=t.get_value(), color={c_theta}))\n")
        context.add_obj("theta_label", "label", f"        theta_label = always_redraw(lambda: MathTex(r'\\theta', color={c_theta}, font_size=24).move_to(Arc(radius=0.5, start_angle=0, angle=t.get_value()).point_from_proportion(0.5)))\n")
        
        # Moving labels for sin/cos values
        context.add_obj("cos_val_label", "label", f"        cos_val_label = always_redraw(lambda: MathTex(r'\\cos(\\theta)', color={c_cos}, font_size=24).next_to(cos_line, DOWN, buff=0.1))\n")
        context.add_obj("sin_val_label", "label", f"        sin_val_label = always_redraw(lambda: MathTex(r'\\sin(\\theta)', color={c_sin}, font_size=24).next_to(sin_line, RIGHT, buff=0.1))\n")

        # Right angle indicator
        context.add_obj("right_angle", "shape", "        right_angle = always_redraw(lambda: RightAngle(cos_line, sin_line, length=0.1, quadrant=(1,1) if np.sin(t.get_value()) >= 0 else (1,-1)))\n")

        # 4. Pedagogical Labels (Fixed positions)
        context.add_obj("header", "label", "        header = Text('The Unit Circle', font_size=36).to_edge(UP, buff=0.5)\n")
        context.add_obj("identity", "label", f"        identity = MathTex(r'\\cos^2(\\theta) + \\sin^2(\\theta) = 1', font_size=32).to_corner(DL, buff=0.5)\n")

        # 5. Animations
        context.add_anim("        self.play(Create(ax), Create(circle), Write(header))\n")
        context.add_anim("        self.play(Create(radius_line), Create(cos_line), Create(sin_line), Create(dot), Create(theta_arc), Write(theta_label))\n")
        context.add_anim("        self.play(Create(right_angle), Write(cos_val_label), Write(sin_val_label), Write(identity))\n")
        context.add_anim("        self.wait(1)\n")
        context.add_anim(f"        self.play(t.animate.set_value(TAU), run_time={rt}, rate_func=linear)\n")
        context.add_anim("        self.wait(2)\n")

class TrigComparisonTemplate(CompositionAwareTemplate):
    """Template for comparing multiple trigonometric functions on the same axes."""
    def compose(self, context: CompositionContext) -> None:
        funcs = self.parameters.get("functions", ["sin", "cos"])
        colors = self.parameters.get("colors", ["GREEN", "RED"])
        x_range = self.parameters.get("x_range", [0, TAU, PI/2])
        
        # Ensure x_range is a list of numbers (avoid type mismatch)
        if isinstance(x_range, str):
            try:
                x_range = eval(x_range)
            except:
                x_range = [0, 6.28, 1.57]

        # Axes
        if not context.object_exists("axes"):
            ax_code = f"        ax = Axes(x_range={x_range}, y_range=[-1.5, 1.5], axis_config={{'include_tip': True}})\n"
            context.add_obj("axes", "axes", ax_code)
        
        # Plot each function
        import re
        for i, func_expr in enumerate(funcs):
            color = colors[i % len(colors)]
            
            # Handle both "sin" and "sin(x)**2" formats gracefully
            clean_expr = func_expr.replace("sin(", "np.sin(").replace("cos(", "np.cos(")
            if clean_expr == "sin":
                clean_expr = "np.sin(x)"
            elif clean_expr == "cos":
                clean_expr = "np.cos(x)"
            elif "(x)" not in clean_expr:
                 # fallback for bare functions like "tan"
                 clean_expr = f"np.{clean_expr}(x)"
                 
            safe_id = re.sub(r'\W+', '_', func_expr).strip('_')
            curve_id = f"curve_{safe_id}"
            
            curve_code = f"        {curve_id} = ax.plot(lambda x: {clean_expr}, color={color})\n"
            context.add_obj(curve_id, "curve", curve_code)
            
            label_id = f"label_{safe_id}"
            label_text = func_expr.replace("**2", "^2")
            label_code = f"        {label_id} = MathTex(r'{label_text}', color={color}).next_to(ax.c2p({x_range[1]}, 0), UP).shift(LEFT*2 + DOWN*{i})\n"
            context.add_obj(label_id, "label", label_code)
            
            context.add_anim(f"        self.play(Create({curve_id}), Write({label_id}))\n")
        
        context.add_anim("        self.wait(2)\n")

class TrigWavesTemplate(CompositionAwareTemplate):
    def compose(self, context: CompositionContext) -> None:
        expr = self.parameters.get("expression", "np.sin(x)")
        color = self.parameters.get("color", "GREEN")
        rt = self.parameters.get("run_time", 6)
        
        context.add_obj("ax_wave", "axes", "        ax = Axes(x_range=[0, TAU, PI/2], y_range=[-1.5, 1.5], axis_config={'include_tip': True}).scale(0.8).to_edge(RIGHT)\n")
        context.add_obj("circle_ax", "axes", "        circle_ax = Axes(x_range=[-1.2, 1.2], y_range=[-1.2, 1.2]).scale(0.8).to_edge(LEFT)\n")
        context.add_obj("circle_wave", "circle", "        circle = Circle(radius=circle_ax.get_x_unit_size() * 0.8, color=WHITE).move_to(circle_ax.c2p(0, 0))\n")
        context.add_obj("t_wave", "tracker", "        t = ValueTracker(0)\n")
        context.add_obj("dot_wave", "dot", "        dot = always_redraw(lambda: Dot(color=YELLOW).move_to(circle_ax.c2p(0.8*np.cos(t.get_value()), 0.8*np.sin(t.get_value()))))\n")
        context.add_obj("curve_wave", "curve", f"        curve = always_redraw(lambda: ax.plot(lambda x: {expr}, x_range=[0, t.get_value()], color={color}))\n")
        
        context.add_anim("        self.play(Create(circle_ax), Create(circle), Create(ax))\n")
        context.add_anim("        self.add(dot, curve)\n")
        context.add_anim(f"        self.play(t.animate.set_value(TAU), run_time={rt}, rate_func=linear)\n")
        context.add_anim("        self.wait(2)\n")
