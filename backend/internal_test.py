from manim import *

config.background_color = '#0a0a0f'

class Scene1(Scene):
    def construct(self):
        # Scene initialization
        # --- Objects Initialization ---
        # axes: axes
        ax = Axes(x_range=[-1.5, 1.5], y_range=[-1.5, 1.5], axis_config={'include_tip': True})
        # circle: circle
        circle = Circle(radius=ax.get_x_unit_size(), color=WHITE).move_to(ax.c2p(0, 0))
        # t: tracker
        t = ValueTracker(0)
        # dot: dot
        dot = always_redraw(lambda: Dot(ax.c2p(np.cos(t.get_value()), np.sin(t.get_value())), color=YELLOW))
        # line: line
        line = always_redraw(lambda: Line(ax.c2p(0, 0), dot.get_center(), color=YELLOW))
        # cos_line: line
        cos_line = always_redraw(lambda: Line(ax.c2p(0, 0), ax.c2p(np.cos(t.get_value()), 0), color=RED, stroke_width=6))
        # sin_line: line
        sin_line = always_redraw(lambda: Line(ax.c2p(np.cos(t.get_value()), 0), dot.get_center(), color=GREEN, stroke_width=6))
        # cos_label: label
        cos_label = MathTex(r'\\cos(\\theta)', color=RED).to_corner(UL)
        # sin_label: label
        sin_label = MathTex(r'\\sin(\\theta)', color=GREEN).next_to(cos_label, DOWN)

        # --- Animations ---
        self.play(Create(ax), Create(circle))
        self.add(line, dot, cos_line, sin_line, cos_label, sin_label)
        self.play(t.animate.set_value(TAU), run_time=8, rate_func=linear)
        self.wait(2)
