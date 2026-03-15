from typing import Any, Dict
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate

class DerivativeTangentTemplate(BaseTemplate):
    """Template for showing the derivative as a tangent line moving along a curve."""
    
    def generate_construct_code(self) -> str:
        expression = self.parameters.get("expression", "x**2")
        code = f"        # Derivative & Tangent Pattern\n"
        code += f"        ax = Axes(x_range=[-3, 3], y_range=[-1, 9], axis_config={{'include_tip': True}})\n"
        code += f"        curve = ax.plot(lambda x: {expression}, color=BLUE)\n"
        code += f"        \n"
        code += f"        t = ValueTracker(-2)\n"
        code += f"        dot = always_redraw(lambda: Dot(color=YELLOW).move_to(ax.c2p(t.get_value(), t.get_value()**2)))\n"
        code += f"        tangent = always_redraw(lambda: ax.get_tangent_line(t.get_value(), curve, length=4, color=YELLOW))\n"
        code += f"        \n"
        code += f"        self.play(Create(ax), Create(curve))\n"
        code += f"        self.play(FadeIn(dot), Create(tangent))\n"
        code += f"        self.play(t.animate.set_value(2), run_time=4, rate_func=linear)\n"
        code += f"        self.wait(2)\n"
        return code

class IntegralAreaTemplate(BaseTemplate):
    """Template for showing the integral as the area under a curve."""
    
    def generate_construct_code(self) -> str:
        expression = self.parameters.get("expression", "x**2")
        x_range = self.parameters.get("x_range", [0, 2])
        code = f"        # Integral & Area Pattern\n"
        code += f"        ax = Axes(x_range=[-1, 3], y_range=[-1, 9])\n"
        code += f"        curve = ax.plot(lambda x: {expression}, color=BLUE)\n"
        code += f"        area = ax.get_area(curve, x_range={x_range}, color=TEAL, opacity=0.5)\n"
        code += f"        \n"
        code += f"        self.play(Create(ax), Create(curve))\n"
        code += f"        self.play(FadeIn(area, shift=UP*0.5), run_time=2)\n"
        code += f"        self.wait(2)\n"
        return code

class GradientDescentTemplate(BaseTemplate):
    """Template for showing gradient descent optimization on a curve."""
    
    def generate_construct_code(self) -> str:
        code = f"        # Gradient Descent Pattern\n"
        code += f"        ax = Axes(x_range=[-4, 4], y_range=[-1, 16])\n"
        code += f"        loss_fn = ax.plot(lambda x: x**2, color=PURPLE)\n"
        code += f"        \n"
        code += f"        # Starting point\n"
        code += f"        curr_x = ValueTracker(3.5)\n"
        code += f"        point = always_redraw(lambda: Dot(color=YELLOW).move_to(ax.c2p(curr_x.get_value(), curr_x.get_value()**2)))\n"
        code += f"        \n"
        code += f"        self.play(Create(ax), Create(loss_fn))\n"
        code += f"        self.add(point)\n"
        code += f"        \n"
        code += f"        # Animate steps downhill\n"
        code += f"        for _ in range(5):\n"
        code += f"            new_x = curr_x.get_value() * 0.5\n"
        code += f"            self.play(curr_x.animate.set_value(new_x), run_time=1)\n"
        code += f"        \n"
        code += f"        self.wait(2)\n"
        return code

# Phase 2: Advanced Calculus Templates

class DerivativeSlopeTemplate(CompositionAwareTemplate):
    """Template for understanding derivative as slope of tangent line."""
    def compose(self) -> None:
        expr = self.parameters.get("expression", "x**2")
        x_val = self.parameters.get("x", 1.0)
        
        # Draw axes
        axes_code = f"        ax = Axes(x_range=[-3, 3], y_range=[-1, 9])\n"
        self.create_object("axes", "axes", axes_code)
        
        # Draw curve
        curve_code = f"        curve = ax.plot(lambda x: {expr}, color=BLUE)\n"
        self.create_object("curve", "curve", curve_code)
        
        anim_code = "        self.play(Create(ax), Create(curve))\n"
        self.add_animation_code(anim_code)
        
        # Place point on curve
        point_code = f"        point = Dot(ax.c2p({x_val}, {x_val}**2), color=YELLOW)\n"
        self.create_object("point", "dot", point_code)
        
        # Draw tangent line
        tangent_code = f"        # Slope at x={x_val}: 2*{x_val} = {2*x_val}\n        tangent = Line([-2, 0], [2, 0], color=GOLD)\n"
        self.create_object("tangent", "line", tangent_code)
        
        anim_code = "        self.play(FadeIn(point), Create(tangent))\n"
        self.add_animation_code(anim_code)

class IntegralAccumulationTemplate(CompositionAwareTemplate):
    """Template for integral as cumulative sum/area."""
    def compose(self) -> None:
        expr = self.parameters.get("expression", "x**2")
        x_range = self.parameters.get("x_range", [0, 2])
        
        # Axes
        axes_code = f"        ax = Axes(x_range=[-1, 3], y_range=[-1, 5])\n"
        self.create_object("axes", "axes", axes_code)
        
        # Function curve
        curve_code = f"        curve = ax.plot(lambda x: {expr}, color=BLUE)\n"
        self.create_object("curve", "curve", curve_code)
        
        # Area under curve
        area_code = f"        area = ax.get_area(curve, x_range={x_range}, color=TEAL, opacity=0.5)\n"
        self.create_object("area", "area", area_code, {"x_range": x_range})
        
        anim_code = "        self.play(Create(ax), Create(curve), FadeIn(area))\n"
        self.add_animation_code(anim_code)

class ChainRuleTemplate(CompositionAwareTemplate):
    """Template for visualizing the chain rule."""
    def compose(self) -> None:
        # Outer function
        outer_code = "        outer_fn = ax.plot(lambda x: x**2, color=BLUE)\n"
        self.create_object("outer_fn", "curve", outer_code)
        
        # Inner function
        inner_code = "        inner_fn = ax.plot(lambda x: x + 1, color=RED)\n"
        self.create_object("inner_fn", "curve", inner_code)
        
        # Composition
        comp_code = "        # d/dx[f(g(x))] = f'(g(x)) * g'(x)\n"
        self.add_animation_code(comp_code)

class GradientDescentAdvancedTemplate(CompositionAwareTemplate):
    """Advanced template for gradient descent with learning rate visualization."""
    def compose(self) -> None:
        # Loss landscape
        axes_code = "        ax = Axes(x_range=[-4, 4], y_range=[-1, 16])\n"
        self.create_object("axes", "axes", axes_code)
        
        # Loss function (parabola)
        loss_code = "        loss = ax.plot(lambda x: x**2, color=PURPLE)\n"
        self.create_object("loss", "curve", loss_code)
        
        # Starting point
        start_code = "        point = Dot(ax.c2p(3.5, 12.25), color=YELLOW)\n"
        self.create_object("point", "dot", start_code)
        
        anim_code = "        self.play(Create(ax), Create(loss), FadeIn(point))\n"
        self.add_animation_code(anim_code)
