from typing import Any, Dict, List, Optional, Type

# Algorithms
from app.templates.algorithms.templates import (
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

    use_3d = _scenes_need_3d(scenes)
    base_class = "ThreeDScene" if use_3d else "Scene"

    code = f"from manim import *\nimport numpy as np\n\nconfig.background_color = '{bg_color}'\n\nclass Scene1({base_class}):\n    def construct(self):\n"
    if use_3d:
        code += "        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)\n"

    for i, s in enumerate(scenes):
        sid = s.get("scene_id", f"s{i}")
        tmpls = s.get("templates", [])
        params = s.get("parameters", {})

        # Inject global style into template parameters
        if isinstance(params, dict):
            params["style"] = style_name
        elif isinstance(params, list):
            for p in params:
                if isinstance(p, dict):
                    p["style"] = style_name

        if tmpls:
            sc_code = render_composed_scene(sid, tmpls, params)
            # Lines already have indentation, just join them
            code += "\n".join([l for l in sc_code.split("\n") if l.strip()]) + "\n"
        else:
            tname = s.get("template", "generic")
            # For the generic template, pass the full scene dict so that
            # GenericAnimationTemplate can access `objects` and `animations`.
            sc_params = s if tname == "generic" else params
            sc_code = render_template(tname, sc_params, False)
            code += "\n".join([l for l in sc_code.split("\n") if l.strip()]) + "\n"
        if i < len(scenes) - 1:
            code += "        self.play(FadeOut(*self.mobjects))\n        self.wait(1)\n"
    return code
