from typing import Any, Dict, List

from app.templates.base import BaseTemplate


def _num(val, default: float) -> float:
    """Safely convert a parameter value to float; fall back to default."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_text(val: Any, default: str = "") -> str:
    """Convert text-like values to a safely escaped Python string payload."""
    if val is None:
        return default
    text = str(val)
    return text.replace("\\", "\\\\").replace("'", "\\'")


class GenericAnimationTemplate(BaseTemplate):
    """Fallback template that interprets general primitives and actions."""

    def generate_construct_code(self) -> str:
        # Check if we are rendering a single scene or a list of scenes
        if "objects" in self.parameters or "animations" in self.parameters:
            scenes = [self.parameters]
        else:
            scenes = self.parameters.get("scenes", [])

        code = "        # Generic Primitive Animation Sequence\n"

        if not scenes:
            code += "        pass\n"
            return code

        for scene in scenes:
            scene_id = scene.get("scene_id", "scene")
            code += f"        # Scene: {scene_id}\n"

            # Create objects
            for obj in scene.get("objects", []):
                obj_id = obj["id"]
                obj_type_raw = str(obj["type"])
                obj_type = obj_type_raw.strip().lower().replace("-", "_").replace(" ", "_")
                params = obj.get("parameters", {})

                if obj_type == "circle":
                    radius = _num(params.get("radius"), 1.0)
                    color = params.get("color", "BLUE")
                    code += f"        {obj_id} = Circle(radius={radius}, color={color})\n"
                elif obj_type == "star":
                    code += f"        {obj_id} = Star(color=GOLD)\n"
                elif obj_type in ("square",):
                    side = _num(params.get("side_length", params.get("side")), 2.0)
                    color = params.get("color", "WHITE")
                    code += f"        {obj_id} = Square(side_length={side}, color={color})\n"
                elif obj_type in ("rectangle", "rect"):
                    width = _num(params.get("width"), 3.0)
                    height = _num(params.get("height"), 2.0)
                    color = params.get("color", "BLUE")
                    code += f"        {obj_id} = Rectangle(width={width}, height={height}, color={color})\n"
                elif obj_type == "triangle":
                    code += f"        {obj_id} = Triangle(color=GREEN)\n"
                elif obj_type == "hexagon":
                    code += f"        {obj_id} = RegularPolygon(n=6, color=YELLOW)\n"
                elif obj_type == "ellipse":
                    width = params.get("width", 3.0)
                    height = params.get("height", 1.5)
                    color = params.get("color", "TEAL")
                    code += f"        {obj_id} = Ellipse(width={width}, height={height}, color={color})\n"
                elif obj_type == "polygon":
                    sides = params.get("sides", 5)
                    code += f"        {obj_id} = RegularPolygon(n={sides}, color=PURPLE)\n"
                elif obj_type == "dot":
                    code += f"        {obj_id} = Dot(color=WHITE)\n"
                elif obj_type in ("text", "label"):
                    text = _safe_text(params.get("text", params.get("label", "")))
                    font_size = params.get("font_size", 32)
                    code += f"        {obj_id} = Text(r'{text}', font_size={font_size})\n"
                elif obj_type in ("math_tex", "mathtex", "latex", "formula", "equation"):
                    expr = params.get("expression", params.get("text", "x")).replace("\\", "\\\\")
                    code += f"        {obj_id} = MathTex(r'{expr}')\n"
                elif obj_type in ("matrix", "determinant"):
                    entries = params.get("entries")
                    latex = params.get("latex", params.get("expression"))
                    if isinstance(entries, list):
                        code += f"        {obj_id} = Matrix({entries})\n"
                    elif latex:
                        code += f"        {obj_id} = MathTex(r'{_safe_text(latex)}')\n"
                    else:
                        code += f"        {obj_id} = Matrix([[1, 2], [3, 4]])\n"
                elif obj_type == "vector":
                    coords = params.get("coords", [1, 1, 0])
                    code += f"        {obj_id} = Vector({coords})\n"
                elif obj_type == "line":
                    start = params.get("start", [-1, 0, 0])
                    end = params.get("end", [1, 0, 0])
                    code += f"        {obj_id} = Line({start}, {end})\n"
                elif obj_type == "arrow":
                    start = params.get("start", [-1, 0, 0])
                    end = params.get("end", [1, 0, 0])
                    code += f"        {obj_id} = Arrow({start}, {end})\n"
                elif obj_type in ("number_line", "numberline"):
                    x_min = params.get("x_min", -3)
                    x_max = params.get("x_max", 3)
                    code += f"        {obj_id} = NumberLine(x_range=[{x_min}, {x_max}, 1], include_numbers=True)\n"
                elif obj_type in ("axes", "axis", "coordinate_system"):
                    code += f"        {obj_id} = Axes(x_range=[-4, 4, 1], y_range=[-3, 3, 1]).scale(0.7)\n"
                elif obj_type == "brace":
                    # Brace needs a target; use a placeholder square
                    code += f"        {obj_id}_target = Square(side_length=2)\n"
                    code += f"        {obj_id} = Brace({obj_id}_target, direction=DOWN)\n"
                # --- 3D objects ---
                elif obj_type in ("cube", "box", "rectangular_prism"):
                    side = _num(params.get("side_length", params.get("side")), 2.0)
                    color = params.get("color", "BLUE")
                    code += f"        {obj_id} = Cube(side_length={side}, fill_opacity=0.7, fill_color={color})\n"
                elif obj_type in ("sphere", "ball"):
                    radius = _num(params.get("radius"), 1.0)
                    color = params.get("color", "BLUE_D")
                    code += f"        {obj_id} = Sphere(radius={radius})\n"
                    code += f"        {obj_id}.set_color({color})\n"
                elif obj_type == "cylinder":
                    radius = _num(params.get("radius"), 1.0)
                    height = _num(params.get("height"), 2.0)
                    color = params.get("color", "GREEN")
                    code += f"        {obj_id} = Cylinder(radius={radius}, height={height})\n"
                    code += f"        {obj_id}.set_color({color})\n"
                elif obj_type == "cone":
                    base_radius = _num(params.get("base_radius", params.get("radius")), 1.0)
                    height = _num(params.get("height"), 2.0)
                    color = params.get("color", "RED")
                    code += f"        {obj_id} = Cone(base_radius={base_radius}, height={height})\n"
                    code += f"        {obj_id}.set_color({color})\n"
                elif obj_type in ("torus", "donut"):
                    major_r = _num(params.get("major_radius"), 1.5)
                    minor_r = _num(params.get("minor_radius"), 0.5)
                    code += f"        {obj_id} = Torus(major_radius={major_r}, minor_radius={minor_r})\n"
                elif obj_type in ("3d_axes", "threedaxes", "3d_coordinate_system"):
                    code += f"        {obj_id} = ThreeDAxes()\n"
                elif obj_type in ("surface", "3d_surface", "parametric_surface"):
                    expr = params.get("expression", "np.sin(u) * np.cos(v)")
                    code += f"        {obj_id} = Surface(\n"
                    code += f"            lambda u, v: np.array([u, v, {expr}]),\n"
                    code += f"            u_range=[-PI, PI], v_range=[-PI, PI],\n"
                    code += f"            resolution=(15, 15)\n"
                    code += f"        )\n"
                    code += f"        {obj_id}.set_style(fill_opacity=0.7)\n"
                elif obj_type in ("image", "mnist_image", "digit_image"):
                    label = _safe_text(params.get("label", params.get("text", "Image")), "Image")
                    code += f"        {obj_id}_frame = RoundedRectangle(width=2.2, height=2.2, corner_radius=0.15, color=BLUE_C, fill_opacity=0.2)\n"
                    code += f"        {obj_id}_label = Text(r'{label}', font_size=20)\n"
                    code += f"        {obj_id}_label.move_to({obj_id}_frame.get_center())\n"
                    code += f"        {obj_id} = VGroup({obj_id}_frame, {obj_id}_label)\n"
                elif obj_type in ("token", "word", "subword"):
                    token_text = _safe_text(
                        params.get("text", params.get("token", "token")), "token"
                    )
                    code += f"        {obj_id}_box = RoundedRectangle(width=1.8, height=0.7, corner_radius=0.1, color=TEAL, fill_opacity=0.2)\n"
                    code += f"        {obj_id}_label = Text(r'{token_text}', font_size=20)\n"
                    code += f"        {obj_id}_label.move_to({obj_id}_box.get_center())\n"
                    code += f"        {obj_id} = VGroup({obj_id}_box, {obj_id}_label)\n"
                elif obj_type in ("state", "markov_state", "node", "graph_node"):
                    label = _safe_text(params.get("label", params.get("text", obj_id)), obj_id)
                    code += f"        {obj_id}_node = Circle(radius=0.45, color=BLUE)\n"
                    code += f"        {obj_id}_label = Text(r'{label}', font_size=20).move_to({obj_id}_node.get_center())\n"
                    code += f"        {obj_id} = VGroup({obj_id}_node, {obj_id}_label)\n"
                elif obj_type == "neural_network":
                    layers = params.get("layers", [4, 5, 3])
                    code += f"        {obj_id} = VGroup()\n"
                    code += f"        _layer_sizes = {layers}\n"
                    code += f"        for _li, _size in enumerate(_layer_sizes):\n"
                    code += f"            _layer = VGroup(*[Circle(radius=0.14, color=BLUE_C, stroke_width=2) for _ in range(int(_size))])\n"
                    code += f"            _layer.arrange(DOWN, buff=0.2)\n"
                    code += f"            _layer.move_to([_li * 1.4 - (len(_layer_sizes)-1)*0.7, 0, 0])\n"
                    code += f"            {obj_id}.add(_layer)\n"
                elif obj_type == "backpropagation":
                    code += f"        {obj_id}_arrow = Arrow(RIGHT*2.2, LEFT*2.2, color=RED)\n"
                    code += f"        {obj_id}_label = Text('Backprop', font_size=22, color=RED).next_to({obj_id}_arrow, UP, buff=0.1)\n"
                    code += f"        {obj_id} = VGroup({obj_id}_arrow, {obj_id}_label)\n"
                else:
                    # Catch-all: create a labelled text so animations don't NameError
                    fallback_label = obj_type_raw.replace("_", " ").title()
                    code += f"        {obj_id} = Text('{_safe_text(fallback_label)}', font_size=28)  # fallback for type '{obj_type_raw}'\n"

                # Set initial position
                pos = params.get("position", [0, 0, 0])
                code += f"        {obj_id}.move_to({pos})\n"

            # Run animations
            for anim in scene.get("animations", []):
                obj_id = anim["object_id"]
                action = str(anim["action"]).strip().lower().replace("-", "_")
                params = anim.get("parameters", {})

                if action in ("fade_in", "appear", "show_up", "reveal"):
                    code += f"        self.play(FadeIn({obj_id}))\n"
                elif action in ("fade_out", "disappear", "hide"):
                    code += f"        self.play(FadeOut({obj_id}))\n"
                elif action == "write":
                    code += f"        self.play(Write({obj_id}))\n"
                elif action == "grow":
                    code += f"        self.play(GrowFromCenter({obj_id}))\n"
                elif action == "move":
                    to_pos = params.get("to", [2, 0, 0])
                    code += f"        self.play({obj_id}.animate.move_to({to_pos}))\n"
                elif action == "scale":
                    factor = params.get("factor", 2.0)
                    code += f"        self.play({obj_id}.animate.scale({factor}))\n"
                elif action == "rotate":
                    angle = params.get("angle", 90)
                    code += f"        self.play(Rotate({obj_id}, angle={angle}*DEGREES))\n"
                elif action == "color":
                    new_color = params.get("color", "YELLOW")
                    code += f"        self.play({obj_id}.animate.set_color({new_color}))\n"
                elif action in ("pulse", "highlight", "indicate"):
                    code += f"        self.play(Indicate({obj_id}))\n"
                elif action in ("create", "draw", "show"):
                    code += f"        self.play(Create({obj_id}))\n"
                elif action == "wait":
                    duration = params.get("duration", 1)
                    code += f"        self.wait({duration})\n"
                elif action == "transform":
                    target_id = params.get("target")
                    if target_id:
                        code += f"        self.play(ReplacementTransform({obj_id}, {target_id}))\n"
                elif action == "connect":
                    target_id = params.get("target")
                    if target_id:
                        line_id = f"{obj_id}_{target_id}_edge"
                        code += f"        {line_id} = Line({obj_id}.get_center(), {target_id}.get_center(), color=GRAY)\n"
                        code += f"        self.play(Create({line_id}))\n"
                elif action == "follow_path":
                    path_type = params.get("path", "circle")
                    if path_type == "circle":
                        code += f"        path = Circle(radius=2)\n"
                        code += f"        self.play(MoveAlongPath({obj_id}, path))\n"
                else:
                    # Unknown action: default to FadeIn so we don't silently skip
                    code += (
                        f"        self.play(FadeIn({obj_id}))  # fallback for action '{action}'\n"
                    )

            code += "        self.wait(1)\n"
        return code
