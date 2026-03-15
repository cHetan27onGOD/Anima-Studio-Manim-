from typing import Any, Dict, List
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate

class UnitCircleTemplate(BaseTemplate):
    """Template for showing the unit circle with sin and cos projections."""
    
    def generate_construct_code(self) -> str:
        code = f"        # Unit Circle Pattern\n"
        code += f"        ax = Axes(x_range=[-1.5, 1.5], y_range=[-1.5, 1.5], axis_config={{'include_tip': True}})\n"
        code += f"        circle = Circle(radius=1, color=WHITE)\n"
        code += f"        \n"
        code += f"        t = ValueTracker(0)\n"
        code += f"        dot = always_redraw(lambda: Dot(ax.c2p(np.cos(t.get_value()), np.sin(t.get_value())), color=YELLOW))\n"
        code += f"        line = always_redraw(lambda: Line(ax.c2p(0, 0), dot.get_center(), color=YELLOW))\n"
        code += f"        cos_line = always_redraw(lambda: Line(ax.c2p(0, 0), ax.c2p(np.cos(t.get_value()), 0), color=RED, stroke_width=6))\n"
        code += f"        sin_line = always_redraw(lambda: Line(ax.c2p(np.cos(t.get_value()), 0), dot.get_center(), color=GREEN, stroke_width=6))\n"
        code += f"        \n"
        code += f"        cos_label = MathTex('cos(\\theta)', color=RED).to_corner(UL)\n"
        code += f"        sin_label = MathTex('sin(\\theta)', color=GREEN).next_to(cos_label, DOWN)\n"
        code += f"        \n"
        code += f"        self.play(Create(ax), Create(circle))\n"
        code += f"        self.add(line, dot, cos_line, sin_line, cos_label, sin_label)\n"
        code += f"        self.play(t.animate.set_value(TAU), run_time=8, rate_func=linear)\n"
        code += f"        self.wait(2)\n"
        return code

class TrigWavesTemplate(BaseTemplate):
    """Template for showing sine and cosine waves generated from the unit circle."""
    
    def generate_construct_code(self) -> str:
        code = f"        # Trig Waves Pattern\n"
        code += f"        ax = Axes(x_range=[0, TAU, PI/2], y_range=[-1.5, 1.5], axis_config={{'include_tip': True}}).scale(0.8).to_edge(RIGHT)\n"
        code += f"        circle_ax = Axes(x_range=[-1.2, 1.2], y_range=[-1.2, 1.2]).scale(0.8).to_edge(LEFT)\n"
        code += f"        circle = Circle(radius=0.8, color=WHITE).move_to(circle_ax.c2p(0, 0))\n"
        code += f"        \n"
        code += f"        t = ValueTracker(0)\n"
        code += f"        dot = always_redraw(lambda: Dot(color=YELLOW).move_to(circle_ax.c2p(0.8*np.cos(t.get_value()), 0.8*np.sin(t.get_value()))))\n"
        code += f"        \n"
        code += f"        sin_curve = always_redraw(lambda: ax.plot(lambda x: np.sin(x), x_range=[0, t.get_value()], color=GREEN))\n"
        code += f"        \n"
        code += f"        self.play(Create(circle_ax), Create(circle), Create(ax))\n"
        code += f"        self.add(dot, sin_curve)\n"
        code += f"        self.play(t.animate.set_value(TAU), run_time=6, rate_func=linear)\n"
        code += f"        self.wait(2)\n"
        return code
