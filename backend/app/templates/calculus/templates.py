from typing import Any, Dict
import numpy as np
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, CompositionContext

PI = np.pi
TAU = 2 * PI

class DerivativeTangentTemplate(BaseTemplate):
    """Template for showing the derivative as a tangent line moving along a curve."""
    
    def generate_construct_code(self) -> str:
        expression = self.parameters.get("expression", "x**2")
        primary_color = self.get_style_param("primary_color", "BLUE")
        accent_color = self.get_style_param("accent_color", "YELLOW")
        axis_color = self.get_style_param("axis_color", "GREY")
        
        code = f"        # Derivative & Tangent Pattern\n"
        code += f"        ax = Axes(x_range=[-3, 3], y_range=[-1, 9], axis_config={{'include_tip': True, 'color': '{axis_color}'}})\n"
        code += f"        curve = ax.plot(lambda x: {expression}, color='{primary_color}')\n"
        code += f"        \n"
        code += f"        t = ValueTracker(-2)\n"
        code += f"        dot = always_redraw(lambda: Dot(color='{accent_color}').move_to(ax.c2p(t.get_value(), t.get_value()**2)))\n"
        code += f"        tangent = always_redraw(lambda: ax.get_tangent_line(t.get_value(), curve, length=4, color='{accent_color}'))\n"
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
        primary_color = self.get_style_param("primary_color", "BLUE")
        accent_color = self.get_style_param("accent_color", "TEAL")
        axis_color = self.get_style_param("axis_color", "GREY")
        
        code = f"        # Integral & Area Pattern\n"
        code += f"        ax = Axes(x_range=[-1, 3], y_range=[-1, 9], axis_config={{'color': '{axis_color}'}})\n"
        code += f"        curve = ax.plot(lambda x: {expression}, color='{primary_color}')\n"
        code += f"        area = ax.get_area(curve, x_range={x_range}, color='{accent_color}', opacity=0.5)\n"
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
    def compose(self, context: "CompositionContext") -> None:
        expr = self.parameters.get("expression", "x**2")
        x_val = self.parameters.get("x", 1.0)
        primary_color = self.get_style_param("primary_color", "BLUE")
        accent_color = self.get_style_param("accent_color", "YELLOW")
        axis_color = self.get_style_param("axis_color", "GREY")
        
        # Draw axes
        axes_code = f"        ax = Axes(x_range=[-3, 3], y_range=[-1, 9], axis_config={{'color': '{axis_color}'}})\n"
        context.add_obj("axes", "axes", axes_code)
        
        # Draw curve
        curve_code = f"        curve = ax.plot(lambda x: {expr}, color='{primary_color}')\n"
        context.add_obj("curve", "curve", curve_code)
        
        anim_code = "        self.play(Create(ax), Create(curve))\n"
        context.add_anim(anim_code)
        
        # Place point on curve
        point_code = f"        point = Dot(ax.c2p({x_val}, {x_val}**2, 0), color='{accent_color}')\n"
        context.add_obj("point", "dot", point_code)
        
        # Draw tangent line
        # For x^2, derivative is 2x. Tangent line point-slope: y - y0 = m(x - x0)
        m = 2 * x_val
        y0 = x_val**2
        # Use two points to define the line for stability
        x1, x2 = x_val - 1, x_val + 1
        y1, y2 = y0 + m*(x1 - x_val), y0 + m*(x2 - x_val)
        
        tangent_code = f"        # Slope at x={x_val}: {m}\n"
        tangent_code += f"        tangent = Line(ax.c2p({x1}, {y1}, 0), ax.c2p({x2}, {y2}, 0), color='{accent_color}')\n"
        context.add_obj("tangent", "line", tangent_code)
        
        # Animation
        anim_code = "        self.play(FadeIn(point), Create(tangent))\n"
        context.add_anim(anim_code)

class IntegralAccumulationTemplate(CompositionAwareTemplate):
    """Template for integral as cumulative sum/area."""
    def compose(self, context: "CompositionContext") -> None:
        expr = self.parameters.get("expression", "x**2")
        x_range = self.parameters.get("x_range", [0, 2])
        
        # Axes
        axes_code = f"        ax = Axes(x_range=[-1, 3], y_range=[-1, 5])\n"
        context.add_obj("axes", "axes", axes_code)
        
        # Function curve
        curve_code = f"        curve = ax.plot(lambda x: {expr}, color=BLUE)\n"
        context.add_obj("curve", "curve", curve_code)
        
        # Area under curve
        area_code = f"        area = ax.get_area(curve, x_range={x_range}, color=TEAL, opacity=0.5)\n"
        context.add_obj("area", "area", area_code, {"x_range": x_range})
        
        anim_code = "        self.play(Create(ax), Create(curve), FadeIn(area))\n"
        context.add_anim(anim_code)

class ChainRuleTemplate(CompositionAwareTemplate):
    """Template for visualizing the chain rule."""
    def compose(self, context: "CompositionContext") -> None:
        # Outer function
        outer_code = "        outer_fn = ax.plot(lambda x: x**2, color=BLUE)\n"
        context.add_obj("outer_fn", "curve", outer_code)
        
        # Inner function
        inner_code = "        inner_fn = ax.plot(lambda x: x + 1, color=RED)\n"
        context.add_obj("inner_fn", "curve", inner_code)
        
        # Composition
        comp_code = "        # d/dx[f(g(x))] = f'(g(x)) * g'(x)\n"
        context.add_anim(comp_code)

class GradientDescentAdvancedTemplate(CompositionAwareTemplate):
    """Advanced template for gradient descent with learning rate visualization."""
    def compose(self, context: "CompositionContext") -> None:
        # Loss landscape
        axes_code = "        ax = Axes(x_range=[-4, 4], y_range=[-1, 16])\n"
        context.add_obj("axes", "axes", axes_code)
        
        # Loss function (parabola)
        loss_code = "        loss = ax.plot(lambda x: x**2, color=PURPLE)\n"
        context.add_obj("loss", "curve", loss_code)
        
        # Starting point
        start_code = "        point = Dot(ax.c2p(3.5, 12.25, 0), color=YELLOW)\n"
        context.add_obj("point", "dot", start_code)
        
        anim_code = "        self.play(Create(ax), Create(loss), FadeIn(point))\n"
        context.add_anim(anim_code)

class PowerRuleTemplate(CompositionAwareTemplate):
    """Template for explaining the power rule: d/dx[x^n] = nx^(n-1)."""
    def compose(self, context: "CompositionContext") -> None:
        n = float(self.parameters.get("power", 2.0))
        
        # Axes
        if not context.object_exists("axes"):
            ax_code = f"        ax = Axes(x_range=[-2, 2], y_range=[-1, 4])\n"
            context.add_obj("axes", "axes", ax_code)
        
        # Plot f(x) = x^n
        curve_code = f"        curve = ax.plot(lambda x: x**{n}, color=BLUE)\n"
        context.add_obj("curve", "curve", curve_code)
        
        # Plot f'(x) = nx^(n-1)
        deriv_code = f"        deriv = ax.plot(lambda x: {n} * x**({n}-1), color=RED)\n"
        context.add_obj("deriv", "curve", deriv_code)
        
        # Labels
        label_f = f"        label_f = MathTex(r'f(x) = x^{{{n}}}', color=BLUE).to_corner(UL)\n"
        context.add_obj("label_f", "label", label_f)
        
        label_df = f"        label_df = MathTex(r'f\\'(x) = {n}x^{{{n-1}}}', color=RED).next_to(label_f, DOWN)\n"
        context.add_obj("label_df", "label", label_df)
        
        context.add_anim("        self.play(Create(ax), Create(curve), Write(label_f))\n")
        context.add_anim("        self.wait(1)\n")
        context.add_anim("        self.play(Create(deriv), Write(label_df))\n")
        context.add_anim("        self.wait(2)\n")

class TaylorSeriesTemplate(CompositionAwareTemplate):
    """Template for visualizing Taylor series approximations."""
    def compose(self, context: "CompositionContext") -> None:
        expr = self.parameters.get("expression", "np.sin(x)")
        approx_level = int(self.parameters.get("level", 3))
        
        # Axes
        if not context.object_exists("axes"):
            ax_code = f"        ax = Axes(x_range=[-PI, PI], y_range=[-1.5, 1.5])\n"
            context.add_obj("axes", "axes", ax_code)
        
        # Original function
        curve_code = f"        curve = ax.plot(lambda x: {expr}, color=BLUE)\n"
        context.add_obj("curve", "curve", curve_code)
        
        context.add_anim("        self.play(Create(ax), Create(curve))\n")
        
        # Show approximation
        # (Simplified: just showing a polynomial)
        poly_code = f"        poly = ax.plot(lambda x: x - (x**3)/6 + (x**5)/120, color=YELLOW)\n"
        context.add_obj("poly", "curve", poly_code)
        
        context.add_anim("        self.play(Create(poly))\n")
        context.add_anim("        self.wait(2)\n")
