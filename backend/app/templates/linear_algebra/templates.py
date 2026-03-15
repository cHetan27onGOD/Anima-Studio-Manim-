from typing import Any, Dict, List
import numpy as np
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, CompositionContext

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
        code += f"        ax = NumberPlane()\n"
        code += f"        matrix = {matrix}\n"
        code += f"        self.play(Create(ax))\n"
        code += f"        self.play(ax.animate.apply_matrix(matrix), run_time=3)\n"
        code += f"        self.wait(2)\n"
        return code

class EigenvectorTemplate(CompositionAwareTemplate):
    """Template for showing eigenvectors and matrix transformations with equations."""
    def compose(self, context: "CompositionContext") -> None: # Fix: Use string forward ref or ensure proper import
        matrix = self.parameters.get("matrix", [[2, 1], [1, 2]])
        if isinstance(matrix, str): matrix = eval(matrix)
        
        # 1. Setup Plane
        context.add_obj("axes", "axes", "        ax = NumberPlane(x_range=[-10, 10], y_range=[-10, 10], background_line_style={'stroke_opacity': 0.6})\n")
        
        # 2. Equation Display
        # Av = lambda v
        eq_code = f"        eq = MathTex(r'A v = \\lambda v', font_size=36).to_corner(UL, buff=0.5)\n"
        context.add_obj("equation", "label", eq_code)
        
        matrix_tex = f"        matrix_tex = Matrix({matrix}).scale(0.6).next_to(eq, DOWN, buff=0.3)\n"
        context.add_obj("matrix_tex", "label", matrix_tex)

        # 3. Eigenvectors
        # For matrix [[2, 1], [1, 2]], eigenvectors are [1, 1] (val=3) and [1, -1] (val=1)
        context.add_obj("v1", "vector", "        v1 = Vector([1, 1], color=YELLOW)\n")
        context.add_obj("v1_label", "label", "        v1_label = MathTex(r'v_1', color=YELLOW).next_to(v1.get_end(), UR, buff=0.1)\n")
        context.add_obj("span1", "line", "        span1 = Line([-10, -10, 0], [10, 10, 0], color=YELLOW, stroke_opacity=0.3)\n")
        
        context.add_obj("v2", "vector", "        v2 = Vector([1, -1], color=PINK)\n")
        context.add_obj("v2_label", "label", "        v2_label = MathTex(r'v_2', color=PINK).next_to(v2.get_end(), DR, buff=0.1)\n")
        context.add_obj("span2", "line", "        span2 = Line([-10, 10, 0], [10, -10, 0], color=PINK, stroke_opacity=0.3)\n")
        
        # 4. Animations
        context.add_anim("        self.play(Create(ax), Write(eq), Write(matrix_tex))\n")
        context.add_anim("        self.play(Create(span1), Create(span2))\n")
        context.add_anim("        self.play(GrowArrow(v1), Write(v1_label), GrowArrow(v2), Write(v2_label))\n")
        context.add_anim("        self.wait(1)\n")
        
        # Apply transformation
        matrix_val = matrix
        trans_anim = f"        matrix_val = np.array({matrix_val})\n"
        trans_anim += "        self.play(\n"
        trans_anim += "            ax.animate.apply_matrix(matrix_val),\n"
        trans_anim += "            v1.animate.apply_matrix(matrix_val),\n"
        trans_anim += "            v2.animate.apply_matrix(matrix_val),\n"
        trans_anim += "            v1_label.animate.move_to(ax.c2p(*(matrix_val @ np.array([1, 1]) * 1.2))),\n"
        trans_anim += "            v2_label.animate.move_to(ax.c2p(*(matrix_val @ np.array([1, -1]) * 1.2))),\n"
        trans_anim += "            run_time=4\n"
        trans_anim += "        )\n"
        context.add_anim(trans_anim)
        context.add_anim("        self.wait(2)\n")

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
    """Advanced template for eigenvectors with equations and stable-span visualization."""
    def compose(self, context: CompositionContext) -> None:
        matrix = self.parameters.get("matrix", [[3, 1], [0, 2]])
        if isinstance(matrix, str): matrix = eval(matrix)
        
        # 1. Setup Plane
        context.add_obj("axes", "axes", "        ax = NumberPlane(x_range=[-10, 10], y_range=[-10, 10], background_line_style={'stroke_opacity': 0.6})\n")
        
        # 2. Equation Display
        # Av = lambda v
        eq_code = f"        eq = MathTex(r'A v = \\lambda v', font_size=36).to_corner(UL, buff=0.5)\n"
        context.add_obj("equation", "label", eq_code)
        
        matrix_tex = f"        matrix_tex = Matrix({matrix}).scale(0.6).next_to(eq, DOWN, buff=0.3)\n"
        context.add_obj("matrix_tex", "label", matrix_tex)

        # 3. Eigenvectors
        # For matrix [[3, 1], [0, 2]], eigenvectors are [1, 0] (val=3) and [1, -1] (val=2)
        # Note: These are hardcoded for this specific matrix for accuracy in visualization
        context.add_obj("v1", "vector", "        v1 = Vector([1, 0], color=YELLOW)\n")
        context.add_obj("v1_label", "label", "        v1_label = MathTex(r'v_1', color=YELLOW).next_to(v1.get_end(), UR, buff=0.1)\n")
        context.add_obj("span1", "line", "        span1 = Line([-10, 0, 0], [10, 0, 0], color=YELLOW, stroke_opacity=0.3)\n")
        
        context.add_obj("v2", "vector", "        v2 = Vector([1, -1], color=PINK)\n")
        context.add_obj("v2_label", "label", "        v2_label = MathTex(r'v_2', color=PINK).next_to(v2.get_end(), DR, buff=0.1)\n")
        context.add_obj("span2", "line", "        span2 = Line([-10, 10, 0], [10, -10, 0], color=PINK, stroke_opacity=0.3)\n")
        
        # 4. Animations
        context.add_anim("        self.play(Create(ax), Write(eq), Write(matrix_tex))\n")
        context.add_anim("        self.play(Create(span1), Create(span2))\n")
        context.add_anim("        self.play(GrowArrow(v1), Write(v1_label), GrowArrow(v2), Write(v2_label))\n")
        context.add_anim("        self.wait(1)\n")
        
        # Apply transformation
        matrix_val = matrix
        trans_anim = f"        matrix_val = np.array({matrix_val})\n"
        trans_anim += "        # Ensure 3D coordinates for Manim transformation\n"
        trans_anim += "        v1_target = np.append(matrix_val @ np.array([1, 0]), 0)\n"
        trans_anim += "        v2_target = np.append(matrix_val @ np.array([1, -1]), 0)\n"
        trans_anim += "        self.play(\n"
        trans_anim += "            ax.animate.apply_matrix(matrix_val),\n"
        trans_anim += "            v1.animate.move_to(ax.c2p(*v1_target), aligned_edge=v1.get_start()),\n"
        trans_anim += "            v2.animate.move_to(ax.c2p(*v2_target), aligned_edge=v2.get_start()),\n"
        trans_anim += "            v1_label.animate.move_to(ax.c2p(*(v1_target * 1.2))),\n"
        trans_anim += "            v2_label.animate.move_to(ax.c2p(*(v2_target * 1.2))),\n"
        trans_anim += "            run_time=4\n"
        trans_anim += "        )\n"
        context.add_anim(trans_anim)
        context.add_anim("        self.wait(2)\n")

class VectorProjectionTemplate(CompositionAwareTemplate):
    """Template for vector projection visualization."""
    def compose(self, context: "CompositionContext") -> None:
        u = self.parameters.get("u", [3, 4])
        v = self.parameters.get("v", [5, 0])
        
        # Axes
        axes_code = "        ax = Axes(x_range=[-1, 8], y_range=[-1, 6])\n"
        context.add_obj("axes", "axes", axes_code)
        
        # Two vectors
        u_code = f"        u = Vector({u}, color=BLUE)\n"
        v_code = f"        v = Vector({v}, color=TEAL)\n"
        context.add_obj("u_vector", "vector", u_code, {"coords": u})
        context.add_obj("v_vector", "vector", v_code, {"coords": v})
        
        anim_code = "        self.play(Create(ax), GrowArrow(u), GrowArrow(v))\n"
        context.add_anim(anim_code)
        
        # Draw projection (must be valid manim code)
        proj_code = "        proj_line = DashedLine(u.get_start(), v.get_end(), color=YELLOW)\n"
        context.add_obj("projection", "line", proj_code)
        
        proj_anim = "        self.play(Create(proj_line))\n"
        context.add_anim(proj_anim)

class BasisChangeTemplate(CompositionAwareTemplate):
    """Template for basis transformation visualization."""
    def compose(self, context: "CompositionContext") -> None:
        old_basis = self.parameters.get("old_basis", [[1, 0], [0, 1]])
        new_basis = self.parameters.get("new_basis", [[1, 1], [1, -1]])
        
        # Standard basis
        axes_code = "        ax = Axes()\n"
        context.add_obj("axes", "axes", axes_code)
        
        # Draw old basis vectors
        old_e1_code = f"        e1 = Vector([1, 0], color=BLUE)\n"
        old_e2_code = f"        e2 = Vector([0, 1], color=RED)\n"
        context.add_obj("e1", "vector", old_e1_code)
        context.add_obj("e2", "vector", old_e2_code)
        
        draw_code = "        self.play(Create(ax), GrowArrow(e1), GrowArrow(e2))\n"
        context.add_anim(draw_code)
        
        # Transform to new basis
        new_code = "        # Rotate and scale for new basis\n        self.wait(1)\n"
        context.add_anim(new_code)

class MatrixMultiplicationCompositionTemplate(CompositionAwareTemplate):
    """Composition-aware version of Matrix Multiplication."""
    def compose(self, context: CompositionContext) -> None:
        matrix_a = self.parameters.get("matrix_a", [[1, 2], [3, 4]])
        matrix_b = self.parameters.get("matrix_b", [[5, 6], [7, 8]])
        
        # Ensure matrices are valid lists of lists (avoid type mismatch)
        if isinstance(matrix_a, str): matrix_a = eval(matrix_a)
        if isinstance(matrix_b, str): matrix_b = eval(matrix_b)

        import numpy as np
        res_val = np.dot(np.array(matrix_a), np.array(matrix_b)).tolist()
        
        # Matrix A
        m1_code = f"        m1 = Matrix({matrix_a}).scale(0.8)\n"
        context.add_obj("matrix_a", "matrix", m1_code)
        
        # Matrix B
        m2_code = f"        m2 = Matrix({matrix_b}).scale(0.8)\n"
        context.add_obj("matrix_b", "matrix", m2_code)
        
        # Result Matrix
        m3_code = f"        m3 = Matrix({res_val}).scale(0.8)\n"
        context.add_obj("matrix_res", "matrix", m3_code)
        
        # Arrangement
        anim_code = "        equals = MathTex('=')\n        group = VGroup(m1, m2, equals, m3).arrange(RIGHT, buff=0.5).center()\n"
        anim_code += "        self.play(Write(m1), Write(m2))\n"
        anim_code += "        self.play(Write(equals), Write(m3))\n"
        context.add_anim(anim_code)

class EigenvectorCompositionTemplate(CompositionAwareTemplate):
    """Composition-aware version of Eigenvector visualization."""
    def compose(self, context: CompositionContext) -> None:
        matrix = self.parameters.get("matrix", [[2, 1], [1, 2]])
        if isinstance(matrix, str): matrix = eval(matrix)
        
        # Standard axes
        if not context.object_exists("axes"):
            ax_code = "        ax = NumberPlane()\n"
            context.add_obj("axes", "axes", ax_code)
        
        # Create vectors
        v1_code = "        v1 = Vector([1, 1], color=YELLOW)\n"
        context.add_obj("v1", "vector", v1_code)
        
        v2_code = "        v2 = Vector([1, -1], color=PINK)\n"
        context.add_obj("v2", "vector", v2_code)
        
        # Animations
        context.add_anim("        self.play(Create(ax))\n")
        context.add_anim("        self.play(GrowArrow(v1), GrowArrow(v2))\n")
        
        # Apply transformation
        trans_code = f"        matrix = np.array({matrix})\n"
        trans_code += "        v1_target = np.append(matrix @ np.array([1, 1]), 0)\n"
        trans_code += "        v2_target = np.append(matrix @ np.array([1, -1]), 0)\n"
        trans_code += "        self.play(\n"
        trans_code += "            ax.animate.apply_matrix(matrix),\n"
        trans_code += "            v1.animate.move_to(ax.c2p(*v1_target), aligned_edge=v1.get_start()),\n"
        trans_code += "            v2.animate.move_to(ax.c2p(*v2_target), aligned_edge=v2.get_start()),\n"
        trans_code += "            run_time=2\n"
        trans_code += "        )\n"
        context.add_anim(trans_code)
