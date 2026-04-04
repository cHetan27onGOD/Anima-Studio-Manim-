from manim import *
import numpy as np

config.background_color = '#0a0a0f'
config.frame_rate = 30

class Scene1(Scene):
    def construct(self):
        # Scene initialization
        # --- Objects ---
        # 3c7cbd17_axes: axes
        ax = Axes(x_range=[0.0, 6.2832], y_range=[-3.0, 3.0], axis_config={'include_tip': True})
        # 3c7cbd17_curve: curve
        curve = ax.plot(lambda x: 2*np.sin(3*x), color=BLUE)

        # --- Animations ---
        self.play(Create(curve))
