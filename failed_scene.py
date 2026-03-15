from manim import *

config.background_color = '#0a0a0f'

class Scene1(Scene):
    def construct(self):
        # --- Scene: intro ---
        # Narration: We want to expand the binomial (a + b) squared.
        # Generic Primitive Animation Sequence
        # Scene: intro
        t1 = Text(r'(a + b)^2', font_size=32)
        t1.move_to([0, 3, 0])
        self.play(Write(t1))
        self.wait(1)
        self.play(FadeOut(*self.mobjects))
        self.next_section()
        self.wait(1)

        # --- Scene: setup ---
        # Narration: The area of the rectangle is a^2.
        # Generic Primitive Animation Sequence
        # Scene: setup
        rect1 = Rectangle(width=2, height=1, color=BLUE)
        rect1.move_to([0, 0, 0])
        text1 = Text(r'a^2', font_size=32)
        text1.move_to([0.5, -1, 0])
        self.play(Create(rect1))
        self.play(Write(text1))
        self.wait(1)
        self.play(FadeOut(*self.mobjects))
        self.next_section()
        self.wait(1)

        # --- Scene: addition ---
        # Narration: Now we add the area of another rectangle with width b and height a.
        # Polynomial Factoring Pattern
        title = Tex(r'(a + b)^2').scale(1.2).to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        grid = Square(side_length=4).shift(DOWN*0.5)
        h_line = Line(grid.get_left(), grid.get_right())
        v_line = Line(grid.get_top(), grid.get_bottom())
        self.play(Create(grid), Create(h_line), Create(v_line))
        # Side labels (factors)
        x_label1 = MathTex('x').next_to(grid, LEFT).shift(UP)
        num_label1 = MathTex('2').next_to(grid, LEFT).shift(DOWN)
        x_label2 = MathTex('x').next_to(grid, UP).shift(LEFT)
        num_label2 = MathTex('3').next_to(grid, UP).shift(RIGHT)
        self.play(Write(x_label1), Write(num_label1), Write(x_label2), Write(num_label2))
        term1 = MathTex('x^2').move_to(grid.get_center()).shift(UP+LEFT)
        term2 = MathTex('3x').move_to(grid.get_center()).shift(UP+RIGHT)
        term3 = MathTex('2x').move_to(grid.get_center()).shift(DOWN+LEFT)
        term4 = MathTex('6').move_to(grid.get_center()).shift(DOWN+RIGHT)
        self.play(FadeIn(term1), FadeIn(term2), FadeIn(term3), FadeIn(term4))
        self.wait(1)
        result = MathTex(r' = (x + 2)(x + 3)').next_to(title, RIGHT)
        self.play(Write(result))
        self.wait(2)
        self.play(FadeOut(*self.mobjects))
        self.next_section()
        self.wait(1)

        # --- Scene: addition_result ---
        # Narration: The expanded form is (a + b)^2 = a^2 + 2ab + b^2.
        # Generic Primitive Animation Sequence
        # Scene: addition_result
        text3 = Text(r'(a + b)^2 = a^2 + 2ab + b^2', font_size=32)
        text3.move_to([0, -1.5, 0])
        self.play(Write(text3))
        self.wait(1)
        self.play(FadeOut(*self.mobjects))
        self.next_section()
        self.wait(1)

        # --- Scene: rectangle_area ---
        # Narration: The area of the third rectangle is b^2.
        # Generic Primitive Animation Sequence
        # Scene: rectangle_area
        rect3 = Rectangle(width=1, height=2, color=BLUE)
        rect3.move_to([0, 0, 0])
        text4 = Text(r'+ b^2', font_size=32)
        text4.move_to([0.5, -1, 0])
        self.play(Create(rect3))
        self.play(Write(text4))
        self.wait(1)
        self.play(FadeOut(*self.mobjects))
        self.next_section()
        self.wait(1)

        # --- Scene: final_result ---
        # Narration: The final expanded form is (a + b)^2 = a^2 + 2ab + b^2.
        # Generic Primitive Animation Sequence
        # Scene: final_result
        text5 = Text(r'(a + b)^2 = a^2 + 2ab + b^2', font_size=32)
        text5.move_to([0, -1.5, 0])
        self.play(Write(text5))
        self.wait(1)
        self.play(FadeOut(*self.mobjects))
        self.next_section()
        self.wait(1)

        # --- Scene: insight ---
        # Narration: We can visualize this expansion using geometric rectangles.
        # Generic Primitive Animation Sequence
        # Scene: insight
        text6 = Text(r'This expansion can be visualized using geometric rectangles.', font_size=32)
        text6.move_to([0, 3, 0])
        self.play(Write(text6))
        self.wait(1)
        self.play(FadeOut(*self.mobjects))
        self.next_section()
        self.wait(1)

        # --- Scene: conclusion ---
        # Narration: This concludes the binomial expansion of (a + b)^2.
        # Generic Primitive Animation Sequence
        # Scene: conclusion
        text7 = Text(r'This concludes the binomial expansion of (a + b)^2.', font_size=32)
        text7.move_to([0, 3, 0])
        self.play(Write(text7))
        self.wait(1)
