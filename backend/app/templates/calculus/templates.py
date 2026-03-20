from typing import Any, Dict
import numpy as np
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, CompositionContext

PI = np.pi
TAU = 2 * PI

class DerivativeTangentTemplate(CompositionAwareTemplate):
    """Template for showing the derivative as a tangent line moving along a curve."""
    def compose(self, context: CompositionContext) -> None:
        expression = self.parameters.get("expression", "x**2")
        primary_color = self.get_style_param("primary_color", "BLUE")
        accent_color = self.get_style_param("accent_color", "YELLOW")
        axis_color = self.get_style_param("axis_color", "GREY")
        
        # Setup Axes
        if not context.object_exists("axes"):
            context.add_obj("axes", "axes", f"        ax = Axes(x_range=[-3, 3], y_range=[-1, 9], axis_config={{'include_tip': True, 'color': '{axis_color}'}})\n")
        
        # Setup Curve
        context.add_obj("curve", "curve", f"        curve = ax.plot(lambda x: {expression}, color='{primary_color}')\n")
        
        # Setup Tracker and Dynamic Elements
        context.add_obj("t", "tracker", "        t = ValueTracker(-2)\n")
        context.add_obj("dot", "dot", f"        dot = always_redraw(lambda: Dot(color='{accent_color}').move_to(ax.c2p(t.get_value(), t.get_value()**2, 0)))\n")
        context.add_obj("tangent", "line", f"        tangent = always_redraw(lambda: ax.get_tangent_line(t.get_value(), curve, length=4, color='{accent_color}'))\n")
        
        # Animations
        context.add_anim("        self.play(Create(ax), Create(curve))\n")
        context.add_anim("        self.play(FadeIn(dot), Create(tangent))\n")
        context.add_anim("        self.play(t.animate.set_value(2), run_time=4, rate_func=linear)\n")
        context.add_anim("        self.wait(2)\n")

class IntegralAreaTemplate(CompositionAwareTemplate):
    """Template for showing the integral as the area under a curve."""
    def compose(self, context: CompositionContext) -> None:
        expression = self.parameters.get("expression", "x**2")
        x_range = self.parameters.get("x_range", [0, 2])
        primary_color = self.get_style_param("primary_color", "BLUE")
        accent_color = self.get_style_param("accent_color", "TEAL")
        axis_color = self.get_style_param("axis_color", "GREY")
        
        # Setup Axes
        if not context.object_exists("axes"):
            context.add_obj("axes", "axes", f"        ax = Axes(x_range=[-1, 3], y_range=[-1, 9], axis_config={{'color': '{axis_color}'}})\n")
        
        # Setup Curve and Area
        context.add_obj("curve", "curve", f"        curve = ax.plot(lambda x: {expression}, color='{primary_color}')\n")
        context.add_obj("area", "area", f"        area = ax.get_area(curve, x_range={x_range}, color='{accent_color}', opacity=0.5)\n")
        
        # Animations
        context.add_anim("        self.play(Create(ax), Create(curve))\n")
        context.add_anim("        self.play(FadeIn(area, shift=UP*0.5), run_time=2)\n")
        context.add_anim("        self.wait(2)\n")

class GradientDescentTemplate(CompositionAwareTemplate):
    """Template for showing gradient descent optimization on a curve."""
    def compose(self, context: CompositionContext) -> None:
        primary_color = self.get_style_param("primary_color", "PURPLE")
        accent_color = self.get_style_param("accent_color", "YELLOW")
        
        # Setup Axes
        if not context.object_exists("axes"):
            context.add_obj("axes", "axes", "        ax = Axes(x_range=[-4, 4], y_range=[-1, 16])\n")
        
        # Setup Loss Function
        context.add_obj("loss_fn", "curve", f"        loss_fn = ax.plot(lambda x: x**2, color='{primary_color}')\n")
        
        # Setup Starting Point
        context.add_obj("curr_x", "tracker", "        curr_x = ValueTracker(3.5)\n")
        context.add_obj("point", "dot", f"        point = always_redraw(lambda: Dot(color='{accent_color}').move_to(ax.c2p(curr_x.get_value(), curr_x.get_value()**2, 0)))\n")
        
        # Animations
        context.add_anim("        self.play(Create(ax), Create(loss_fn))\n")
        context.add_anim("        self.add(point)\n")
        
        # Animate steps downhill
        step_code = (
            "        for _ in range(5):\n"
            "            new_x = curr_x.get_value() * 0.5\n"
            "            self.play(curr_x.animate.set_value(new_x), run_time=1)\n"
        )
        context.add_anim(step_code)
        context.add_anim("        self.wait(2)\n")

# Phase 2: Advanced Calculus Templates

class DerivativeSlopeTemplate(CompositionAwareTemplate):
    """Advanced pedagogical template for derivative slope."""
    def compose(self, context: "CompositionContext") -> None:
        expr = self.parameters.get("expression", "x**2")
        x_val = self.parameters.get("x", 1.5)
        primary_color = self.get_style_param("primary_color", "BLUE")
        accent_color = self.get_style_param("accent_color", "YELLOW")
        axis_color = self.get_style_param("axis_color", "GREY")
        
        # 1. Setup (Axes first)
        context.add_obj("ax", "axes", f"        ax = Axes(x_range=[-3, 3], y_range=[-1, 9], axis_config={{'color': '{axis_color}'}})\n")
        context.add_anim("        self.play(Create(ax))\n")
        
        # 2. Draw Curve
        context.add_obj("curve", "curve", f"        curve = ax.plot(lambda x: {expr}, color='{primary_color}')\n")
        context.add_anim("        self.play(Create(curve))\n")
        
        # 3. Highlight Key Concept (The point)
        # Use ax.c2p to ensure it's locked to the coordinate system
        context.add_obj("point", "dot", f"        point = Dot(ax.c2p({x_val}, {x_val}**2, 0), color='{accent_color}')\n")
        context.add_anim("        self.play(FadeIn(point, scale=0.5))\n")
        
        # 4. Action & Synchronized Labels (The tangent line)
        # Use get_tangent_line to guarantee it's linked to the curve
        context.add_obj("tangent", "line", f"        tangent = ax.get_tangent_line({x_val}, curve, length=4, color='{accent_color}')\n")
        
        # Calculate slope for the label
        m = 2 * x_val
        context.add_obj("slope_label", "label", f"        slope_label = MathTex(r'm = {m}', color='{accent_color}').next_to(tangent, UR, buff=0.1)\n")
        
        context.add_anim("        self.play(Create(tangent), Write(slope_label))\n")
        
        # 5. Emphasize Result
        context.add_anim("        self.play(Indicate(slope_label, scale_factor=1.2), tangent.animate.set_stroke(width=10))\n")
        context.add_anim("        self.wait(2)\n")

class IntegralAccumulationTemplate(CompositionAwareTemplate):
    """Template for integral as cumulative sum/area."""
    def compose(self, context: "CompositionContext") -> None:
        expr = self.parameters.get("expression", "x**2")
        x_range = self.parameters.get("x_range", [0, 2])
        
        # Axes
        axes_code = f"        ax = Axes(x_range=[-1, 3], y_range=[-1, 5])\n"
        context.add_obj("axes", "axes", axes_code)
        
        # Function curve
        curve_code = f"        curve = ax.plot(lambda x: {expr}, color='BLUE')\n"
        context.add_obj("curve", "curve", curve_code)
        
        # Area under curve
        area_code = f"        area = ax.get_area(curve, x_range={x_range}, color='TEAL', opacity=0.5)\n"
        context.add_obj("area", "area", area_code, {"x_range": x_range})
        
        anim_code = "        self.play(Create(ax), Create(curve), FadeIn(area))\\n"
        context.add_anim(anim_code)

class ChainRuleTemplate(CompositionAwareTemplate):
    """Template for visualizing the chain rule."""
    def compose(self, context: "CompositionContext") -> None:
        # Outer function
        outer_code = "        outer_fn = ax.plot(lambda x: x**2, color='BLUE')\\n"
        context.add_obj("outer_fn", "curve", outer_code)
        
        # Inner function
        inner_code = "        inner_fn = ax.plot(lambda x: x + 1, color='RED')\\n"
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
        loss_code = "        loss = ax.plot(lambda x: x**2, color='PURPLE')\\n"
        context.add_obj("loss", "curve", loss_code)
        
        # Starting point
        start_code = "        point = Dot(ax.c2p(3.5, 12.25, 0), color='YELLOW')\\n"
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
        curve_code = f"        curve = ax.plot(lambda x: x**{{n}}, color='BLUE')\\n"
        context.add_obj("curve", "curve", curve_code)
        
        # Plot f'(x) = nx^(n-1)
        deriv_code = f"        deriv = ax.plot(lambda x: {{n}} * x**({{n}}-1), color='RED')\\n"
        context.add_obj("deriv", "curve", deriv_code)
        
        # Labels
        label_f = f"        label_f = MathTex(r'f(x) = x^{{{{n}}}}', color='BLUE').to_corner(UL)\\n"
        context.add_obj("label_f", "label", label_f)
        
        label_df = f"        label_df = MathTex(r'f\\\\'(x) = {{n}}x^{{{{n-1}}}}', color='RED').next_to(label_f, DOWN)\\n"
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
        curve_code = f"        curve = ax.plot(lambda x: {{expr}}, color='BLUE')\\n"
        context.add_obj("curve", "curve", curve_code)
        
        context.add_anim("        self.play(Create(ax), Create(curve))\n")
        
        # Show approximation
        # (Simplified: just showing a polynomial)
        poly_code = f"        poly = ax.plot(lambda x: x - (x**3)/6 + (x**5)/120, color='YELLOW')\\n"
        context.add_obj("poly", "curve", poly_code)
        
        context.add_anim("        self.play(Create(poly))\n")
        context.add_anim("        self.wait(2)\n")
