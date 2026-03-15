from typing import Any, Dict, List
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate

class PolynomialFactoringTemplate(BaseTemplate):
    """Template for showing polynomial factoring using an area model/box method."""
    
    def generate_construct_code(self) -> str:
        expression = self.parameters.get("expression", "x^2 + 5x + 6")
        factors = self.parameters.get("factors", ["(x + 2)", "(x + 3)"])
        
        code = f"        # Polynomial Factoring Pattern\n"
        code += f"        title = MathTex(r'{expression}').scale(1.2).to_edge(UP)\n"
        code += f"        self.play(Write(title))\n"
        code += f"        self.wait(1)\n"
        
        # Create a 2x2 grid for factoring visualization
        code += f"        grid = Square(side_length=4).shift(DOWN*0.5)\n"
        code += f"        h_line = Line(grid.get_left(), grid.get_right())\n"
        code += f"        v_line = Line(grid.get_top(), grid.get_bottom())\n"
        code += f"        \n"
        code += f"        self.play(Create(grid), Create(h_line), Create(v_line))\n"
        
        # Labels for the factors
        code += f"        # Side labels (factors)\n"
        code += f"        x_label1 = MathTex('x').next_to(grid, LEFT).shift(UP)\n"
        code += f"        num_label1 = MathTex('2').next_to(grid, LEFT).shift(DOWN)\n"
        code += f"        x_label2 = MathTex('x').next_to(grid, UP).shift(LEFT)\n"
        code += f"        num_label2 = MathTex('3').next_to(grid, UP).shift(RIGHT)\n"
        code += f"        \n"
        code += f"        self.play(Write(x_label1), Write(num_label1), Write(x_label2), Write(num_label2))\n"
        
        # Inside terms
        code += f"        term1 = MathTex('x^2').move_to(grid.get_center()).shift(UP+LEFT)\n"
        code += f"        term2 = MathTex('3x').move_to(grid.get_center()).shift(UP+RIGHT)\n"
        code += f"        term3 = MathTex('2x').move_to(grid.get_center()).shift(DOWN+LEFT)\n"
        code += f"        term4 = MathTex('6').move_to(grid.get_center()).shift(DOWN+RIGHT)\n"
        
        code += f"        self.play(FadeIn(term1), FadeIn(term2), FadeIn(term3), FadeIn(term4))\n"
        code += f"        self.wait(1)\n"
        
        # Final result
        code += f"        result = MathTex(r' = {factors[0]}{factors[1]}').next_to(title, RIGHT)\n"
        code += f"        self.play(Write(result))\n"
        code += f"        self.wait(2)\n"
        return code

class EquationSolvingTemplate(BaseTemplate):
    """Template for showing step-by-step algebraic equation solving."""
    
    def generate_construct_code(self) -> str:
        steps = self.parameters.get("steps", [
            "2x + 5 = 15",
            "2x = 15 - 5",
            "2x = 10",
            "x = 5"
        ])
        
        code = f"        # Equation Solving Pattern\n"
        code += f"        step_objs = VGroup(*[MathTex(s) for s in {steps}]).arrange(DOWN, buff=0.5).center()\n"
        code += f"        \n"
        code += f"        for i, step in enumerate(step_objs):\n"
        code += f"            if i == 0:\n"
        code += f"                self.play(Write(step))\n"
        code += f"            else:\n"
        code += f"                self.play(TransformMatchingTex(step_objs[i-1].copy(), step))\n"
        code += f"            self.wait(1)\n"
        code += f"        \n"
        code += f"        self.play(Circumscribe(step_objs[-1]))\n"
        code += f"        self.wait(2)\n"
        return code
