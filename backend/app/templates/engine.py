from typing import Any, Dict, Type, List, Optional
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, TemplateComposer
from app.templates.linear_algebra.templates import (
    MatrixMultiplicationTemplate, VectorTransformationTemplate, EigenvectorTemplate, 
    DotProductTemplate, EigenvectorsAdvancedTemplate, VectorProjectionTemplate, 
    BasisChangeTemplate
)
from app.templates.machine_learning.templates import (
    NeuralNetworkTemplate, TransformerAttentionTemplate, BackpropagationTemplate,
    EmbeddingSpaceTemplate, ConvolutionFiltersTemplate
)
from app.templates.calculus.templates import (
    DerivativeTangentTemplate, IntegralAreaTemplate, GradientDescentTemplate,
    DerivativeSlopeTemplate, IntegralAccumulationTemplate, ChainRuleTemplate,
    GradientDescentAdvancedTemplate
)
from app.templates.algorithms.templates import (
    BFSTraversalTemplate, GraphVisualizationTemplate, DFSTraversalTemplate,
    DijkstraTemplate, TopologicalSortTemplate, SortingTemplate
)
from app.templates.trigonometry.templates import (
    UnitCircleTemplate, TrigWavesTemplate
)
from app.templates.algebra.templates import (
    PolynomialFactoringTemplate, EquationSolvingTemplate
)
from app.templates.generic import GenericAnimationTemplate
from app.templates.primitives import (
    DrawCurveTemplate, 
    PlacePointTemplate, 
    DrawArrowTemplate, 
    HighlightObjectTemplate,
    DrawAxisTemplate,
    WriteTextTemplate,
    CreateVectorTemplate,
    TransformObjectTemplate
)

TEMPLATES: Dict[str, Type[BaseTemplate]] = {
    # Phase 1: Classic Templates
    "matrix_multiplication": MatrixMultiplicationTemplate,
    "vector_transformation": VectorTransformationTemplate,
    "eigenvector": EigenvectorTemplate,
    "dot_product": DotProductTemplate,
    "neural_network": NeuralNetworkTemplate,
    "transformer_attention": TransformerAttentionTemplate,
    "derivative_tangent": DerivativeTangentTemplate,
    "integral_area": IntegralAreaTemplate,
    "gradient_descent": GradientDescentTemplate,
    "bfs_traversal": BFSTraversalTemplate,
    
    # Phase 2: Advanced Composition-Aware Templates
    "eigenvectors_advanced": EigenvectorsAdvancedTemplate,
    "vector_projection": VectorProjectionTemplate,
    "basis_change": BasisChangeTemplate,
    "derivative_slope": DerivativeSlopeTemplate,
    "integral_accumulation": IntegralAccumulationTemplate,
    "chain_rule": ChainRuleTemplate,
    "gradient_descent_advanced": GradientDescentAdvancedTemplate,
    "backpropagation": BackpropagationTemplate,
    "embedding_spaces": EmbeddingSpaceTemplate,
    "convolution_filters": ConvolutionFiltersTemplate,
    "graph_visualization": GraphVisualizationTemplate,
    "dfs_traversal": DFSTraversalTemplate,
    "dijkstra": DijkstraTemplate,
    "topological_sort": TopologicalSortTemplate,
    "sorting": SortingTemplate,
    
    # Phase 2: Algebra Templates
    "polynomial_factoring": PolynomialFactoringTemplate,
    "equation_solving": EquationSolvingTemplate,
    
    # Phase 2: Trig Templates
    "unit_circle": UnitCircleTemplate,
    "trig_waves": TrigWavesTemplate,
    
    # Micro-templates (Primitives)
    "generic": GenericAnimationTemplate,
    "draw_curve": DrawCurveTemplate,
    "place_point": PlacePointTemplate,
    "draw_arrow": DrawArrowTemplate,
    "highlight_object": HighlightObjectTemplate,
    "draw_axis": DrawAxisTemplate,
    "write_text": WriteTextTemplate,
    "create_vector": CreateVectorTemplate,
    "transform_object": TransformObjectTemplate,
}

def get_template(template_name: str) -> Type[BaseTemplate]:
    """Get a template class by name."""
    if template_name not in TEMPLATES:
        # Fallback to generic template if not found
        return GenericAnimationTemplate
    return TEMPLATES[template_name]

def is_composition_aware(template_cls: Type[BaseTemplate]) -> bool:
    """Check if a template is composition-aware (supports composition mode)."""
    return issubclass(template_cls, CompositionAwareTemplate)

def render_template(template_name: str, parameters: Dict[str, Any], include_header: bool = True) -> str:
    """Render a template with parameters to Manim code."""
    template_cls = get_template(template_name)
    template = template_cls(parameters)
    
    if include_header:
        return template.generate_code()
    else:
        return template.generate_construct_code()

def render_composed_scene(scene_id: str, templates_list: List[str], parameters: Dict[str, Any]) -> str:
    """
    Render a scene composed of multiple micro-templates with state sharing.
    
    Args:
        scene_id: Unique identifier for the scene
        templates_list: List of template names to compose
        parameters: Parameters for all templates
    
    Returns:
        Manim code with proper object scope management
    """
    composer = TemplateComposer(scene_id)
    
    for template_name in templates_list:
        template_cls = get_template(template_name)
        
        # Check if template is composition-aware
        if is_composition_aware(template_cls):
            template = template_cls(parameters)
            composer.add_template(template)
        else:
            # For legacy templates, create a wrapper
            import logging
            logging.warning(f"Template {template_name} is not composition-aware, falling back to legacy render")
    
    return composer.compose()

def render_multi_scene_plan(plan: Dict[str, Any]) -> str:
    """Render a multi-scene plan into a single Manim script using Scene Graph logic."""
    title = plan.get("title", "Educational Animation")
    # Check both top-level 'scenes' and nested 'parameters.scenes' for robustness
    scenes_data = plan.get("scenes") or plan.get("parameters", {}).get("scenes", [])
    
    # Scene Graph: Sort scenes based on dependencies
    ordered_scenes = _sort_scenes_by_dependency(scenes_data)
    
    # Header
    code = "from manim import *\n\n"
    code += "config.background_color = '#0a0a0f'\n\n"
    code += f"class Scene1(Scene):\n    def construct(self):\n"
    
    if not ordered_scenes:
        code += "        pass\n"
        return code
        
    for i, scene_data in enumerate(ordered_scenes):
        scene_id = scene_data.get("scene_id", f"scene_{i}")
        
        code += f"        # --- Scene: {scene_id} ---\n"
        if scene_data.get("narration"):
            code += f"        # Narration: {scene_data['narration']}\n"
            
        # COMPOSITION MODE: Check if multiple templates are specified
        composed_templates = scene_data.get("templates", [])
        if composed_templates:
            # Use composition framework for stateful rendering
            scene_params = scene_data.get("parameters", {})
            scene_code = render_composed_scene(scene_id, composed_templates, scene_params)
            for line in scene_code.split("\n"):
                if line.strip():
                    code += f"{line}\n"
        else:
            # Single template mode (legacy/default)
            template_name = scene_data.get("template", "generic")
            params = scene_data.get("parameters", {})
            if template_name == "generic":
                params = scene_data
            
            scene_code = render_template(template_name, params, include_header=False)
            for line in scene_code.split("\n"):
                if line.strip():
                    code += f"{line}\n"
        
        # CLEAR SCREEN BETWEEN SCENES TO PREVENT OVERLAP
        # But only if it's not the last scene and we want fresh start
        if i < len(ordered_scenes) - 1:
            code += "        self.play(FadeOut(*self.mobjects))\n"
            code += "        self.next_section()\n"
            code += "        self.wait(1)\n\n"
        
    return code

def _sort_scenes_by_dependency(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort scenes based on their 'depends_on' field."""
    # For now, we'll implement a simple dependency order
    # In a production system, this would be a full topological sort
    scene_map = {s["scene_id"]: s for s in scenes}
    visited = set()
    result = []

    def visit(scene_id):
        if scene_id in visited:
            return
        visited.add(scene_id)
        scene = scene_map.get(scene_id)
        if not scene:
            return
        for dep in scene.get("depends_on", []):
            visit(dep)
        result.append(scene)

    for s in scenes:
        visit(s["scene_id"])
    return result
