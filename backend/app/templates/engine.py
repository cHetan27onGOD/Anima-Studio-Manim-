from typing import Any, Dict, List, Optional, Type

# Algorithms
from app.templates.algorithms.templates import (
    BFSDFSComparisonTemplate,
    BFSTraversalTemplate,
    DFSTraversalTemplate,
    DijkstraTemplate,
    GraphVisualizationTemplate,
    SortingTemplate,
    TopologicalSortTemplate,
)
from app.templates.base import BaseTemplate

# Calculus
from app.templates.calculus.templates import (
    ChainRuleTemplate,
    DerivativeSlopeTemplate,
    DerivativeTangentTemplate,
    GradientDescentAdvancedTemplate,
    GradientDescentTemplate,
    IntegralAccumulationTemplate,
    IntegralAreaTemplate,
    PowerRuleTemplate,
    TaylorSeriesTemplate,
)
from app.templates.composition import CompositionAwareTemplate, TemplateComposer

# Generic fallback
from app.templates.generic import GenericAnimationTemplate

# Linear Algebra
from app.templates.linear_algebra.templates import (
    BasisChangeTemplate,
    DotProductTemplate,
    EigenvectorCompositionTemplate,
    EigenvectorTemplate,
    MatrixMultiplicationCompositionTemplate,
    MatrixMultiplicationTemplate,
    VectorTransformationTemplate,
)

# Machine Learning
from app.templates.machine_learning.templates import (
    BackpropagationTemplate,
    ConvolutionFiltersTemplate,
    EmbeddingSpaceTemplate,
    MnistRecognitionTemplate,
    NeuralNetworkTemplate,
    TransformerAttentionTemplate,
)

# Primitives
from app.templates.primitives import (
    CreateVectorTemplate,
    DrawArrowTemplate,
    DrawAxisTemplate,
    DrawCurveTemplate,
    HighlightObjectTemplate,
    PlacePointTemplate,
    TransformObjectTemplate,
    WriteTextTemplate,
)
from app.templates.styles import get_style

# Trigonometry
from app.templates.trigonometry.templates import (
    TrigComparisonTemplate,
    TrigWavesTemplate,
    UnitCircleTemplate,
)

TEMPLATES: Dict[str, Type[BaseTemplate]] = {
    # Trigonometry
    "unit_circle": UnitCircleTemplate,
    "trig_waves": TrigWavesTemplate,
    "trig_comparison": TrigComparisonTemplate,
    # Calculus
    "derivative_tangent": DerivativeTangentTemplate,
    "integral_area": IntegralAreaTemplate,
    "gradient_descent": GradientDescentTemplate,
    "derivative_slope": DerivativeSlopeTemplate,
    "integral_accumulation": IntegralAccumulationTemplate,
    "chain_rule": ChainRuleTemplate,
    "gradient_descent_advanced": GradientDescentAdvancedTemplate,
    "power_rule": PowerRuleTemplate,
    "taylor_series": TaylorSeriesTemplate,
    # Linear Algebra
    "matrix_multiplication": MatrixMultiplicationTemplate,
    "vector_transformation": VectorTransformationTemplate,
    "eigenvector": EigenvectorTemplate,
    "dot_product": DotProductTemplate,
    "basis_change": BasisChangeTemplate,
    "matrix_multiplication_composition": MatrixMultiplicationCompositionTemplate,
    "eigenvector_composition": EigenvectorCompositionTemplate,
    # Machine Learning
    "neural_network": NeuralNetworkTemplate,
    "transformer_attention": TransformerAttentionTemplate,
    "backpropagation": BackpropagationTemplate,
    "embedding_space": EmbeddingSpaceTemplate,
    "convolution_filters": ConvolutionFiltersTemplate,
    "mnist_recognition": MnistRecognitionTemplate,
    # Algorithms
    "bfs_dfs_comparison": BFSDFSComparisonTemplate,
    "bfs_traversal": BFSTraversalTemplate,
    "graph_visualization": GraphVisualizationTemplate,
    "dfs_traversal": DFSTraversalTemplate,
    "dijkstra": DijkstraTemplate,
    "topological_sort": TopologicalSortTemplate,
    "sorting": SortingTemplate,
    # Primitives
    "draw_curve": DrawCurveTemplate,
    "place_point": PlacePointTemplate,
    "draw_arrow": DrawArrowTemplate,
    "draw_axis": DrawAxisTemplate,
    "write_text": WriteTextTemplate,
    "create_vector": CreateVectorTemplate,
    "transform_object": TransformObjectTemplate,
    "highlight_object": HighlightObjectTemplate,
    # Generic fallback (must follow the specific ones so overrides are possible)
    "generic": GenericAnimationTemplate,
}


def get_template(name: str) -> Type[BaseTemplate]:
    return TEMPLATES.get(name, GenericAnimationTemplate)


def render_template(name: str, params: Dict[str, Any], include_header: bool = True) -> str:
    t_cls = get_template(name)
    t = t_cls(params)
    return t.generate_code() if include_header else t.generate_construct_code()


def render_composed_scene(scene_id: str, templates: List[str], params: Any) -> str:
    composer = TemplateComposer(scene_id)
    for i, name in enumerate(templates):
        t_cls = get_template(name)
        p = (
            params[i]
            if isinstance(params, list) and i < len(params)
            else (params if isinstance(params, dict) else {})
        )
        if issubclass(t_cls, CompositionAwareTemplate):
            composer.add_template(t_cls(p))
    return composer.compose()


_3D_OBJECT_TYPES = {
    "cube",
    "box",
    "rectangular_prism",
    "sphere",
    "ball",
    "cylinder",
    "cone",
    "torus",
    "donut",
    "prism",
    "pyramid",
    "surface",
    "3d_surface",
    "parametric_surface",
    "3d_axes",
    "threedaxes",
    "3d_coordinate_system",
}


def _scenes_need_3d(scenes: List[Dict[str, Any]]) -> bool:
    """Return True if any scene contains a 3D object type."""
    for s in scenes:
        for obj in s.get("objects", []):
            if obj.get("type", "").lower() in _3D_OBJECT_TYPES:
                return True
    return False


def render_multi_scene_plan(plan: Dict[str, Any]) -> str:
    scenes = plan.get("scenes") or plan.get("parameters", {}).get("scenes", [])
    style_name = plan.get("style", "3b1b")
    style = get_style(style_name)
    bg_color = style["background_color"]

    plan_params = plan.get("parameters", {})
    if not isinstance(plan_params, dict):
        plan_params = {}
    render_profile = plan_params.get("render_profile", {})
    if not isinstance(render_profile, dict):
        render_profile = {}

    def _profile_value(key: str, default: Any) -> Any:
        if key in plan_params:
            return plan_params.get(key, default)
        return render_profile.get(key, default)

    quality = str(plan.get("quality", "medium") or "medium").lower()
    default_fps = 60 if quality == "high" else 30
    try:
        frame_rate = int(float(_profile_value("frame_rate", default_fps)))
        if frame_rate <= 0:
            frame_rate = default_fps
    except (TypeError, ValueError):
        frame_rate = default_fps

    try:
        inter_scene_wait = float(_profile_value("inter_scene_wait", 1.0))
    except (TypeError, ValueError):
        inter_scene_wait = 1.0
    inter_scene_wait = max(0.0, inter_scene_wait)

    try:
        transition_fade_duration = float(_profile_value("transition_fade_duration", 0.8))
    except (TypeError, ValueError):
        transition_fade_duration = 0.8
    transition_fade_duration = max(0.0, transition_fade_duration)

    use_3d = _scenes_need_3d(scenes)
    base_class = "ThreeDScene" if use_3d else "Scene"

    code = (
        f"from manim import *\n"
        f"import numpy as np\n\n"
        f"config.background_color = '{bg_color}'\n"
        f"config.frame_rate = {frame_rate}\n\n"
        f"class Scene1({base_class}):\n"
        f"    def construct(self):\n"
    )
    if use_3d:
        code += "        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)\n"

    for i, s in enumerate(scenes):
        sid = s.get("scene_id", f"s{i}")
        tmpls = s.get("templates", [])
        raw_params = s.get("parameters", {})
        params: Any = raw_params

        # Inject global style into template parameters
        if isinstance(params, dict):
            params = dict(params)
            params["style"] = style_name
            if render_profile:
                params.setdefault("render_profile", render_profile)
        elif isinstance(params, list):
            params = [dict(p) if isinstance(p, dict) else p for p in params]
            for p in params:
                if isinstance(p, dict):
                    p["style"] = style_name
                    if render_profile:
                        p.setdefault("render_profile", render_profile)

        if tmpls:
            sc_code = render_composed_scene(sid, tmpls, params)
            # Lines already have indentation, just join them
            code += "\n".join([l for l in sc_code.split("\n") if l.strip()]) + "\n"
        else:
            tname = s.get("template", "generic")
            # For the generic template, pass the full scene dict so that
            # GenericAnimationTemplate can access `objects` and `animations`.
            if tname == "generic":
                sc_params = dict(s)
                if render_profile:
                    sc_params.setdefault("render_profile", render_profile)
            else:
                sc_params = params
            sc_code = render_template(tname, sc_params, False)
            code += "\n".join([l for l in sc_code.split("\n") if l.strip()]) + "\n"
        if i < len(scenes) - 1:
            if transition_fade_duration > 0:
                code += (
                    f"        self.play(FadeOut(*self.mobjects), "
                    f"run_time={transition_fade_duration:.2f})\n"
                )
            else:
                code += "        self.play(FadeOut(*self.mobjects))\n"
            if inter_scene_wait > 0:
                code += f"        self.wait({inter_scene_wait:.2f})\n"
    return code
