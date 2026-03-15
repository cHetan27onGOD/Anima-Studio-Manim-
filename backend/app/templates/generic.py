from typing import Any, Dict, List
from app.templates.base import BaseTemplate

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
                obj_type = obj["type"]
                params = obj.get("parameters", {})
                
                if obj_type == "circle":
                    radius = params.get("radius", 1.0)
                    color = params.get("color", "BLUE")
                    code += f"        {obj_id} = Circle(radius={radius}, color={color})\n"
                elif obj_type == "star":
                    code += f"        {obj_id} = Star(color=GOLD)\n"
                elif obj_type in ("square",):
                    side = params.get("side_length", params.get("side", 2.0))
                    color = params.get("color", "WHITE")
                    code += f"        {obj_id} = Square(side_length={side}, color={color})\n"
                elif obj_type in ("rectangle", "rect"):
                    width = params.get("width", 3.0)
                    height = params.get("height", 2.0)
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
                    text = params.get("text", params.get("label", "")).replace("'", "\'")
                    font_size = params.get("font_size", 32)
                    code += f"        {obj_id} = Text(r'{text}', font_size={font_size})\n"
                elif obj_type in ("math_tex", "mathtex", "latex", "formula", "equation"):
                    expr = params.get("expression", params.get("text", "x")).replace("\\", "\\\\")
                    code += f"        {obj_id} = MathTex(r'{expr}')\n"
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
                else:
                    # Catch-all: create a labelled text so animations don't NameError
                    fallback_label = obj_type.replace("_", " ").title()
                    code += f"        {obj_id} = Text('{fallback_label}', font_size=28)  # fallback for type '{obj_type}'\n"

                # Set initial position
                pos = params.get("position", [0, 0, 0])
                code += f"        {obj_id}.move_to({pos})\n"
            
            # Run animations
            for anim in scene.get("animations", []):
                obj_id = anim["object_id"]
                action = anim["action"]
                params = anim.get("parameters", {})
                
                if action == "fade_in":
                    code += f"        self.play(FadeIn({obj_id}))\n"
                elif action == "fade_out":
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
                elif action == "pulse" or action == "highlight":
                    code += f"        self.play(Indicate({obj_id}))\n"
                elif action == "create" or action == "draw" or action == "show":
                    code += f"        self.play(Create({obj_id}))\n"
                elif action == "wait":
                    duration = params.get("duration", 1)
                    code += f"        self.wait({duration})\n"
                elif action == "transform":
                    target_id = params.get("target")
                    if target_id:
                        code += f"        self.play(ReplacementTransform({obj_id}, {target_id}))\n"
                elif action == "follow_path":
                    path_type = params.get("path", "circle")
                    if path_type == "circle":
                        code += f"        path = Circle(radius=2)\n"
                        code += f"        self.play(MoveAlongPath({obj_id}, path))\n"
                else:
                    # Unknown action: default to FadeIn so we don't silently skip
                    code += f"        self.play(FadeIn({obj_id}))  # fallback for action '{action}'\n"
            
            code += "        self.wait(1)\n"
        return code
