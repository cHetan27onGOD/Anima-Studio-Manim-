from manim import *
import numpy as np

config.background_color = '#0a0a0f'
config.frame_rate = 30

class Scene1(Scene):
    def construct(self):
        title = Text('Evaluate Expression', font_size=34).to_edge(UP)
        self.play(Write(title))
        steps = ["Expression: 2sin(pi/2) + 3cos(0)", "Term 1: 2*sin(pi/2) = 2*1 = 2", "Term 2: 3*cos(0) = 3*1 = 3", "Final value: 5"]
        step_mob = Text(steps[0], font_size=28).next_to(title, DOWN, buff=0.4)
        self.play(FadeIn(step_mob), run_time=0.8)
        self.wait(0.35)
        for line in steps[1:]:
            next_step = Text(line, font_size=26).move_to(step_mob)
            self.play(ReplacementTransform(step_mob, next_step), run_time=0.85)
            step_mob = next_step
            self.wait(0.3)
        self.play(step_mob.animate.to_corner(UL).scale(0.58), run_time=0.7)
        axes = Axes(
            x_range=[-2*np.pi, 2*np.pi, np.pi/2],
            y_range=[-1.6, 1.6, 0.4],
            x_length=8.5,
            y_length=4.6,
            axis_config={'include_tip': False},
        ).to_edge(DOWN)
        self.play(Create(axes), run_time=1.0)
        sin_curve = axes.plot(lambda x: np.sin(x), x_range=[-2*np.pi, 2*np.pi], color=GREEN)
        self.play(Create(sin_curve), run_time=1.0)
        cos_curve = axes.plot(lambda x: np.cos(x), x_range=[-2*np.pi, 2*np.pi], color=BLUE)
        self.play(Create(cos_curve), run_time=1.0)
        trig_terms = [{"function": "sin", "coefficient": 2.0, "angle_expr": "pi/2", "angle": 1.5707963267948966, "base_y": 1.0, "term_value": 2.0}, {"function": "cos", "coefficient": 3.0, "angle_expr": "0", "angle": 0.0, "base_y": 1.0, "term_value": 3.0}]
        for term in trig_terms:
            x_val = float(term['angle'])
            y_val = float(term['base_y'])
            dot_color = GREEN if term['function'] == 'sin' else BLUE
            dot = Dot(axes.c2p(x_val, y_val), color=dot_color)
            lbl = Text(f"{term['function']}({term['angle_expr']})={y_val:.2f}", font_size=20).next_to(dot, UP, buff=0.12)
            self.play(FadeIn(dot), FadeIn(lbl), run_time=0.55)
        result = Text('Result = 5', font_size=30, color=YELLOW).to_edge(DOWN)
        self.play(FadeIn(result), run_time=0.9)
        self.wait(1.8)
