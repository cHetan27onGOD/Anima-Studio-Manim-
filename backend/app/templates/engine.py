from typing import Any, Dict, Type, List, Optional
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, TemplateComposer
from app.templates.styles import get_style

# Trigonometry
from app.templates.trigonometry.templates import (
    UnitCircleTemplate, TrigWavesTemplate, TrigComparisonTemplate
)

# Calculus
from app.templates.calculus.templates import (
    DerivativeTangentTemplate, IntegralAreaTemplate, GradientDescentTemplate,
    DerivativeSlopeTemplate, IntegralAccumulationTemplate, ChainRuleTemplate,
    GradientDescentAdvancedTemplate, PowerRuleTemplate, TaylorSeriesTemplate
)

# Linear Algebra
from app.templates.linear_algebra.templates import (
    MatrixMultiplicationTemplate, VectorTransformationTemplate, EigenvectorTemplate,
    DotProductTemplate, BasisChangeTemplate, MatrixMultiplicationCompositionTemplate,
    EigenvectorCompositionTemplate
)

# Machine Learning
from app.templates.machine_learning.templates import (
    NeuralNetworkTemplate, TransformerAttentionTemplate, BackpropagationTemplate,
    EmbeddingSpaceTemplate, ConvolutionFiltersTemplate
)

# Algorithms
from app.templates.algorithms.templates import (
    BFSTraversalTemplate, GraphVisualizationTemplate, DFSTraversalTemplate,
    DijkstraTemplate, TopologicalSortTemplate
)

# Primitives
from app.templates.primitives import (
    DrawCurveTemplate, PlacePointTemplate, DrawArrowTemplate, 
    DrawAxisTemplate, WriteTextTemplate, CreateVectorTemplate, 
    TransformObjectTemplate, HighlightObjectTemplate
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
    
    # Algorithms
    "bfs_traversal": BFSTraversalTemplate,
    "graph_visualization": GraphVisualizationTemplate,
    "dfs_traversal": DFSTraversalTemplate,
    "dijkstra": DijkstraTemplate,
    "topological_sort": TopologicalSortTemplate,
    
    # Primitives
    "draw_curve": DrawCurveTemplate,
    "place_point": PlacePointTemplate,
    "draw_arrow": DrawArrowTemplate,
    "draw_axis": DrawAxisTemplate,
    "write_text": WriteTextTemplate,
    "create_vector": CreateVectorTemplate,
    "transform_object": TransformObjectTemplate,
    "highlight_object": HighlightObjectTemplate,
}

def get_template(name: str) -> Type[BaseTemplate]:
    return TEMPLATES.get(name, DrawCurveTemplate)

def render_template(name: str, params: Dict[str, Any], include_header: bool = True) -> str:
    t_cls = get_template(name)
    t = t_cls(params)
    return t.generate_code() if include_header else t.generate_construct_code()

def render_composed_scene(scene_id: str, templates: List[str], params: Any) -> str:
    composer = TemplateComposer(scene_id)
    for i, name in enumerate(templates):
        t_cls = get_template(name)
        p = params[i] if isinstance(params, list) and i < len(params) else (params if isinstance(params, dict) else {})
        if issubclass(t_cls, CompositionAwareTemplate):
            composer.add_template(t_cls(p))
    return composer.compose()

def render_multi_scene_plan(plan: Dict[str, Any]) -> str:
    scenes = plan.get("scenes") or plan.get("parameters", {}).get("scenes", [])
    style_name = plan.get("style", "3b1b")
    style = get_style(style_name)
    bg_color = style["background_color"]
    
    code = f"from manim import *\nimport numpy as np\n\nconfig.background_color = '{bg_color}'\n\nclass Scene1(Scene):\n    def construct(self):\n"
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
            tname = s.get("template", "draw_curve")
            sc_code = render_template(tname, params, False)
            code += "\n".join([l for l in sc_code.split("\n") if l.strip()]) + "\n"
        if i < len(scenes) - 1:
            code += "        self.play(FadeOut(*self.mobjects))\n        self.wait(1)\n"
    return code
