import re
from typing import Any, Dict

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
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove control chars that can break generated source readability.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    return text


def _py_literal(val: Any, default: str = "") -> str:
    """Return a safe Python string literal for generated source code."""
    return repr(_safe_text(val, default))


def _safe_identifier(name: Any, default: str = "obj") -> str:
    """Create a valid Python identifier from LLM-provided ids."""
    ident = re.sub(r"[^0-9a-zA-Z_]", "_", str(name or "").strip())
    ident = re.sub(r"_+", "_", ident).strip("_")
    if not ident:
        ident = default
    if ident[0].isdigit():
        ident = f"{default}_{ident}"
    return ident


_ACTION_BASE_DURATIONS = {
    "fade_in": 0.6,
    "fade_out": 0.6,
    "write": 1.8,
    "grow": 1.1,
    "move": 1.2,
    "scale": 1.0,
    "rotate": 1.0,
    "color": 0.8,
    "pulse": 0.8,
    "highlight": 0.8,
    "indicate": 0.8,
    "create": 1.2,
    "draw": 1.2,
    "show": 1.0,
    "transform": 1.4,
    "connect": 1.0,
    "follow_path": 1.8,
}


class GenericAnimationTemplate(BaseTemplate):
    """Fallback template that interprets general primitives and actions."""

    def generate_construct_code(self) -> str:
        render_profile = self.parameters.get("render_profile", {})
        if not isinstance(render_profile, dict):
            render_profile = {}

        pace_scale = _num(
            render_profile.get("pace_scale", self.parameters.get("pace_scale", 1.0)), 1.0
        )
        pace_scale = max(0.5, min(3.0, pace_scale))
        inter_action_wait = _num(render_profile.get("inter_action_wait", 0.0), 0.0)
        inter_action_wait = max(0.0, inter_action_wait)
        scene_pause = _num(render_profile.get("scene_pause", 1.0), 1.0)
        scene_pause = max(0.0, scene_pause)

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

            id_remap: Dict[str, str] = {}
            existing_ids: set[str] = set()

            # Create objects
            for obj_idx, obj in enumerate(scene.get("objects", []), start=1):
                raw_obj_id = obj.get("id", f"obj_{obj_idx}")
                base_obj_id = _safe_identifier(raw_obj_id, f"obj_{obj_idx}")
                obj_id = base_obj_id
                suffix = 2
                while obj_id in existing_ids:
                    obj_id = f"{base_obj_id}_{suffix}"
                    suffix += 1
                existing_ids.add(obj_id)
                id_remap[str(raw_obj_id)] = obj_id
                id_remap[obj_id] = obj_id

                obj_type_raw = str(obj.get("type", "text"))
                obj_type = obj_type_raw.strip().lower().replace("-", "_").replace(" ", "_")
                params = obj.get("parameters", {}) or {}

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
                    text_lit = _py_literal(params.get("text", params.get("label", "")))
                    font_size = params.get("font_size", 32)
                    code += f"        {obj_id} = Text({text_lit}, font_size={font_size})\n"
                elif obj_type in ("math_tex", "mathtex", "latex", "formula", "equation"):
                    expr_lit = _py_literal(params.get("expression", params.get("text", "x")), "x")
                    code += f"        {obj_id} = MathTex({expr_lit})\n"
                elif obj_type in ("matrix", "determinant"):
                    entries = params.get("entries")
                    latex = params.get("latex", params.get("expression"))
                    if isinstance(entries, list):
                        code += f"        {obj_id} = Matrix({entries})\n"
                    elif latex:
                        code += f"        {obj_id} = MathTex({_py_literal(latex)})\n"
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
                    code += "            u_range=[-PI, PI], v_range=[-PI, PI],\n"
                    code += "            resolution=(15, 15)\n"
                    code += "        )\n"
                    code += f"        {obj_id}.set_style(fill_opacity=0.7)\n"
                elif obj_type in ("image", "mnist_image", "digit_image"):
                    label_lit = _py_literal(
                        params.get("label", params.get("text", "Image")), "Image"
                    )
                    code += f"        {obj_id}_frame = RoundedRectangle(width=2.2, height=2.2, corner_radius=0.15, color=BLUE_C, fill_opacity=0.2)\n"
                    code += f"        {obj_id}_label = Text({label_lit}, font_size=20)\n"
                    code += f"        {obj_id}_label.move_to({obj_id}_frame.get_center())\n"
                    code += f"        {obj_id} = VGroup({obj_id}_frame, {obj_id}_label)\n"
                elif obj_type in ("token", "word", "subword"):
                    token_text_lit = _py_literal(
                        params.get("text", params.get("token", "token")), "token"
                    )
                    code += f"        {obj_id}_box = RoundedRectangle(width=1.8, height=0.7, corner_radius=0.1, color=TEAL, fill_opacity=0.2)\n"
                    code += f"        {obj_id}_label = Text({token_text_lit}, font_size=20)\n"
                    code += f"        {obj_id}_label.move_to({obj_id}_box.get_center())\n"
                    code += f"        {obj_id} = VGroup({obj_id}_box, {obj_id}_label)\n"
                elif obj_type in ("state", "markov_state", "node", "graph_node"):
                    label_lit = _py_literal(params.get("label", params.get("text", obj_id)), obj_id)
                    code += f"        {obj_id}_node = Circle(radius=0.45, color=BLUE)\n"
                    code += f"        {obj_id}_label = Text({label_lit}, font_size=20).move_to({obj_id}_node.get_center())\n"
                    code += f"        {obj_id} = VGroup({obj_id}_node, {obj_id}_label)\n"
                elif obj_type == "neural_network":
                    layers = params.get("layers", [4, 5, 3])
                    code += f"        {obj_id} = VGroup()\n"
                    code += f"        _layer_sizes = {layers}\n"
                    code += "        for _li, _size in enumerate(_layer_sizes):\n"
                    code += "            _layer = VGroup(*[Circle(radius=0.14, color=BLUE_C, stroke_width=2) for _ in range(int(_size))])\n"
                    code += "            _layer.arrange(DOWN, buff=0.2)\n"
                    code += "            _layer.move_to([_li * 1.4 - (len(_layer_sizes)-1)*0.7, 0, 0])\n"
                    code += f"            {obj_id}.add(_layer)\n"
                elif obj_type == "backpropagation":
                    code += f"        {obj_id}_arrow = Arrow(RIGHT*2.2, LEFT*2.2, color=RED)\n"
                    code += f"        {obj_id}_label = Text('Backprop', font_size=22, color=RED).next_to({obj_id}_arrow, UP, buff=0.1)\n"
                    code += f"        {obj_id} = VGroup({obj_id}_arrow, {obj_id}_label)\n"
                else:
                    # Catch-all: create a labelled text so animations don't NameError
                    fallback_label = obj_type_raw.replace("_", " ").title()
                    code += f"        {obj_id} = Text({_py_literal(fallback_label)}, font_size=28)  # fallback for type '{obj_type_raw}'\n"

                # Set initial position
                pos = params.get("position", [0, 0, 0])
                code += f"        {obj_id}.move_to({pos})\n"

            # Run animations
            for anim_idx, anim in enumerate(scene.get("animations", []), start=1):
                raw_anim_obj = str(anim.get("object_id", f"auto_obj_{anim_idx}"))
                obj_id = id_remap.get(raw_anim_obj)
                if not obj_id:
                    base_obj_id = _safe_identifier(raw_anim_obj, f"auto_obj_{anim_idx}")
                    obj_id = base_obj_id
                    suffix = 2
                    while obj_id in existing_ids:
                        obj_id = f"{base_obj_id}_{suffix}"
                        suffix += 1
                    existing_ids.add(obj_id)
                    id_remap[raw_anim_obj] = obj_id

                    # Synthesize a safe placeholder object so this animation can still run.
                    placeholder_lit = _py_literal(
                        raw_anim_obj.replace("_", " ").title() or "Concept"
                    )
                    code += f"        {obj_id} = Text({placeholder_lit}, font_size=26)\n"

                action = str(anim.get("action", "fade_in")).strip().lower().replace("-", "_")
                params = anim.get("parameters", {}) or {}
                explicit_duration = _num(anim.get("duration"), 0.0)
                base_duration = (
                    explicit_duration
                    if explicit_duration > 0
                    else _ACTION_BASE_DURATIONS.get(action, 1.0)
                )
                run_time = max(0.2, base_duration * pace_scale)

                if action in ("fade_in", "appear", "show_up", "reveal"):
                    code += f"        self.play(FadeIn({obj_id}), run_time={run_time:.2f})\n"
                elif action in ("fade_out", "disappear", "hide"):
                    code += f"        self.play(FadeOut({obj_id}), run_time={run_time:.2f})\n"
                elif action == "write":
                    code += f"        self.play(Write({obj_id}), run_time={run_time:.2f})\n"
                elif action == "grow":
                    code += (
                        f"        self.play(GrowFromCenter({obj_id}), run_time={run_time:.2f})\n"
                    )
                elif action == "move":
                    to_pos = params.get("to", [2, 0, 0])
                    code += f"        self.play({obj_id}.animate.move_to({to_pos}), run_time={run_time:.2f})\n"
                elif action == "scale":
                    factor = params.get("factor", 2.0)
                    code += (
                        f"        self.play({obj_id}.animate.scale({factor}), "
                        f"run_time={run_time:.2f})\n"
                    )
                elif action == "rotate":
                    angle = params.get("angle", 90)
                    code += (
                        f"        self.play(Rotate({obj_id}, angle={angle}*DEGREES), "
                        f"run_time={run_time:.2f})\n"
                    )
                elif action == "color":
                    new_color = params.get("color", "YELLOW")
                    code += (
                        f"        self.play({obj_id}.animate.set_color({new_color}), "
                        f"run_time={run_time:.2f})\n"
                    )
                elif action in ("pulse", "highlight", "indicate"):
                    code += f"        self.play(Indicate({obj_id}), run_time={run_time:.2f})\n"
                elif action in ("create", "draw", "show"):
                    code += f"        self.play(Create({obj_id}), run_time={run_time:.2f})\n"
                elif action == "wait":
                    duration = _num(params.get("duration", run_time), run_time)
                    code += f"        self.wait({max(0.0, duration):.2f})\n"
                elif action == "transform":
                    target_id = params.get("target")
                    if target_id:
                        raw_target_id = str(target_id)
                        target_id = id_remap.get(
                            raw_target_id, _safe_identifier(raw_target_id, f"target_{anim_idx}")
                        )
                        if target_id not in existing_ids:
                            existing_ids.add(target_id)
                            id_remap[raw_target_id] = target_id
                            target_label_lit = _py_literal(
                                raw_target_id.replace("_", " ").title() or "Target"
                            )
                            code += (
                                f"        {target_id} = Text({target_label_lit}, font_size=24)\n"
                            )
                        code += (
                            f"        self.play(ReplacementTransform({obj_id}, {target_id}), "
                            f"run_time={run_time:.2f})\n"
                        )
                elif action == "connect":
                    target_id = params.get("target")
                    if target_id:
                        raw_target_id = str(target_id)
                        target_id = id_remap.get(
                            raw_target_id, _safe_identifier(raw_target_id, f"target_{anim_idx}")
                        )
                        if target_id not in existing_ids:
                            existing_ids.add(target_id)
                            id_remap[raw_target_id] = target_id
                            target_label_lit = _py_literal(
                                raw_target_id.replace("_", " ").title() or "Target"
                            )
                            code += (
                                f"        {target_id} = Text({target_label_lit}, font_size=24)\n"
                            )
                        line_id = f"{obj_id}_{target_id}_edge"
                        code += f"        {line_id} = Line({obj_id}.get_center(), {target_id}.get_center(), color=GRAY)\n"
                        code += f"        self.play(Create({line_id}), run_time={run_time:.2f})\n"
                elif action == "follow_path":
                    path_type = params.get("path", "circle")
                    if path_type == "circle":
                        code += "        path = Circle(radius=2)\n"
                        code += (
                            f"        self.play(MoveAlongPath({obj_id}, path), "
                            f"run_time={run_time:.2f})\n"
                        )
                else:
                    # Unknown action: default to FadeIn so we don't silently skip
                    code += (
                        f"        self.play(FadeIn({obj_id}), run_time={run_time:.2f})  "
                        f"# fallback for action '{action}'\n"
                    )

                if action != "wait" and inter_action_wait > 0:
                    code += f"        self.wait({inter_action_wait:.2f})\n"

            code += f"        self.wait({scene_pause:.2f})\n"
        return code
