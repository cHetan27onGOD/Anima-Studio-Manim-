from typing import Any, Dict, List
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate

class MatrixMultiplicationTemplate(BaseTemplate):
    """Template for 3Blue1Brown style Matrix Multiplication animations."""
    
    def generate_construct_code(self) -> str:
        matrix_a = self.parameters.get("matrix_a", [[1, 2], [3, 4]])
        matrix_b = self.parameters.get("matrix_b", [[5, 6], [7, 8]])
        
        code = f"        # 3B1B Matrix Multiplication Pattern\n"
        code += f"        matrix_a_val = {matrix_a}\n"
        code += f"        matrix_b_val = {matrix_b}\n"
        code += f"        \n"
        code += f"        m1 = Matrix(matrix_a_val).scale(0.8)\n"
        code += f"        m2 = Matrix(matrix_b_val).scale(0.8)\n"
        code += f"        equals = MathTex('=')\n"
        code += f"        \n"
        code += f"        # Calculate result matrix\n"
        code += f"        import numpy as np\n"
        code += f"        res_val = np.dot(np.array(matrix_a_val), np.array(matrix_b_val)).tolist()\n"
        code += f"        m3 = Matrix(res_val).scale(0.8)\n"
        code += f"        \n"
        code += f"        group = VGroup(m1, m2, equals, m3).arrange(RIGHT, buff=0.5).center()\n"
        code += f"        \n"
        code += f"        self.play(Write(m1), Write(m2))\n"
        code += f"        self.wait(1)\n"
        code += f"        self.play(Write(equals), Write(m3))\n"
        code += f"        self.wait(2)\n"
        
        # Step-by-step highlight logic (Knowledge-based improvement)
        code += f"        # Highlight rows and columns for pedagogical clarity\n"
        code += f"        for i in range(len(matrix_a_val)):\n"
        code += f"            for j in range(len(matrix_b_val[0])):\n"
        code += f"                row_rect = SurroundingRectangle(m1.get_rows()[i], color=YELLOW)\n"
        code += f"                col_rect = SurroundingRectangle(m2.get_columns()[j], color=BLUE)\n"
        code += f"                res_cell = SurroundingRectangle(m3.get_entries()[i*len(matrix_b_val[0]) + j], color=GREEN)\n"
        code += f"                \n"
        code += f"                # Show calculation label (e.g., 3*5 + 4*3 = 27)\n"
        code += f"                calc_str = ' + '.join([f'{{matrix_a_val[i][k]}}*{{matrix_b_val[k][j]}}' for k in range(len(matrix_a_val[0]))])\n"
        code += f"                calc_val = res_val[i][j]\n"
        code += f"                calc_tex = MathTex(f'{{calc_str}} = {{calc_val}}', font_size=24, color=WHITE).to_edge(DOWN, buff=1)\n"
        code += f"                \n"
        code += f"                self.play(Create(row_rect), Create(col_rect))\n"
        code += f"                self.play(Write(calc_tex), Create(res_cell))\n"
        code += f"                self.wait(1)\n"
        code += f"                self.play(FadeOut(row_rect), FadeOut(col_rect), FadeOut(res_cell), FadeOut(calc_tex))\n"
        
        return code

class VectorTransformationTemplate(BaseTemplate):
    """Template for 3Blue1Brown style Linear Transformation animations."""
    
    def generate_construct_code(self) -> str:
        matrix = self.parameters.get("matrix", [[2, 1], [1, 2]])
        code = f"        # Linear Transformation Pattern\n"
        code += f"        self.setup()\n"
        code += f"        matrix = {matrix}\n"
        code += f"        self.apply_matrix(matrix)\n"
        code += f"        self.wait(2)\n"
        return code

class EigenvectorTemplate(BaseTemplate):
    """Template for showing eigenvectors and matrix transformations."""
    
    def generate_construct_code(self) -> str:
        matrix = self.parameters.get("matrix", [[2, 1], [1, 2]])
        code = f"        # Eigenvector Pattern\n"
        code += f"        self.setup()\n"
        code += f"        matrix = {matrix}\n"
        code += f"        \n"
        code += f"        # Create a vector that stays on its line\n"
        code += f"        v1 = Vector([1, 1], color=YELLOW)\n"
        code += f"        v2 = Vector([1, -1], color=PINK)\n"
        code += f"        self.add_vector(v1)\n"
        code += f"        self.add_vector(v2)\n"
        code += f"        \n"
        code += f"        self.apply_matrix(matrix)\n"
        code += f"        self.wait(2)\n"
        return code

class DotProductTemplate(BaseTemplate):
    """Template for explaining the dot product as a projection."""
    
    def generate_construct_code(self) -> str:
        code = f"        # Dot Product Projection Pattern\n"
        code += f"        ax = Axes(x_range=[-1, 5], y_range=[-1, 5])\n"
        code += f"        v1 = Vector([3, 2], color=BLUE)\n"
        code += f"        v2 = Vector([4, 0], color=TEAL)\n"
        code += f"        \n"
        code += f"        self.play(Create(ax), Create(v1), Create(v2))\n"
        code += f"        self.wait(1)\n"
        code += f"        \n"
        code += f"        # Projection line\n"
        code += f"        p_line = DashedLine(v1.get_end(), [3, 0, 0], color=WHITE)\n"
        code += f"        self.play(Create(p_line))\n"
        code += f"        self.wait(2)\n"
        return code

# Phase 2: New Advanced Linear Algebra Templates

class EigenvectorsAdvancedTemplate(CompositionAwareTemplate):
    """Advanced template for eigenvectors with step-by-step visualization."""
    def compose(self) -> None:
        matrix = self.parameters.get("matrix", [[3, 1], [1, 3]])
        
        # Scene 1: Show vector space
        axes_code = "        ax = Axes(x_range=[-4, 4], y_range=[-4, 4])\n"
        self.create_object("axes", "axes", axes_code)
        
        # Scene 2: Random vector
        vec_code = "        vec = Vector([2, 1], color=BLUE)\n"
        self.create_object("vector", "vector", vec_code, {"matrix": matrix})
        
        anim_code = "        self.play(Create(ax), GrowArrow(vec))\n"
        self.add_animation_code(anim_code)
        
        # Scene 3: Apply transformation
        trans_code = f"        transformed = Vector({matrix[0]}*vec[0] + {matrix[1]}*vec[1], color=GOLD)\n"
        self.create_object("transformed_vector", "vector", trans_code)
        
        trans_anim = "        self.play(Transform(vec, transformed))\n"
        self.add_animation_code(trans_anim)

class VectorProjectionTemplate(CompositionAwareTemplate):
    """Template for vector projection visualization."""
    def compose(self) -> None:
        u = self.parameters.get("u", [3, 4])
        v = self.parameters.get("v", [5, 0])
        
        # Axes
        axes_code = "        ax = Axes(x_range=[-1, 8], y_range=[-1, 6])\n"
        self.create_object("axes", "axes", axes_code)
        
        # Two vectors
        u_code = f"        u = Vector({u}, color=BLUE)\n"
        v_code = f"        v = Vector({v}, color=TEAL)\n"
        self.create_object("u_vector", "vector", u_code, {"coords": u})
        self.create_object("v_vector", "vector", v_code, {"coords": v})
        
        anim_code = "        self.play(Create(ax), GrowArrow(u), GrowArrow(v))\n"
        self.add_animation_code(anim_code)
        
        # Draw projection
        proj_code = "        proj_line = DashedLine(u_start, v_end, color=YELLOW)\n"
        self.create_object("projection", "line", proj_code)
        
        proj_anim = "        self.play(Create(proj_line))\n"
        self.add_animation_code(proj_anim)

class BasisChangeTemplate(CompositionAwareTemplate):
    """Template for basis transformation visualization."""
    def compose(self) -> None:
        old_basis = self.parameters.get("old_basis", [[1, 0], [0, 1]])
        new_basis = self.parameters.get("new_basis", [[1, 1], [1, -1]])
        
        # Standard basis
        axes_code = "        ax = Axes()\n"
        self.create_object("axes", "axes", axes_code)
        
        # Draw old basis vectors
        old_e1_code = f"        e1 = Vector([1, 0], color=BLUE)\n"
        old_e2_code = f"        e2 = Vector([0, 1], color=RED)\n"
        self.create_object("e1", "vector", old_e1_code)
        self.create_object("e2", "vector", old_e2_code)
        
        draw_code = "        self.play(Create(ax), GrowArrow(e1), GrowArrow(e2))\n"
        self.add_animation_code(draw_code)
        
        # Transform to new basis
        new_code = "        # Rotate and scale for new basis\n        self.wait(1)\n"
        self.add_animation_code(new_code)
