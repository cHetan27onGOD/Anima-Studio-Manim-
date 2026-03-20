from typing import Set, Dict, List, Type, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemplateCapabilities:
    template_id: str
    name: str
    description: str
    concepts: Set[str] = field(default_factory=set)
    composition_ready: bool = False
    estimated_duration: float = 5.0
    domain: str = "general"  # calculus | linear_algebra | algorithms | ml | trigonometry | general

    def matches_concept(self, concept: str) -> float:
        if concept.lower() in [c.lower() for c in self.concepts]:
            return 1.0
        for c in self.concepts:
            if concept.lower() in c.lower() or c.lower() in concept.lower():
                return 0.7
        return 0.0


class CapabilityRegistry:
    def __init__(self):
        self.registry: Dict[str, TemplateCapabilities] = {}

    def register(self, caps: TemplateCapabilities):
        self.registry[caps.template_id] = caps

    def find_templates_for_concept(
        self, concept: str, composition_mode: bool = False, domain: Optional[str] = None
    ) -> List[str]:
        matches = []
        # If domain is 'general', we should match against all templates
        effective_domain = domain if domain != "general" else None
        
        for tid, caps in self.registry.items():
            if composition_mode and not caps.composition_ready:
                continue
            if effective_domain and caps.domain != effective_domain and caps.domain != "general":
                continue
            score = caps.matches_concept(concept)
            if score > 0:
                matches.append((tid, score))
        matches.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches]

    def find_templates_for_domain(self, domain: str) -> List[str]:
        """Return all template IDs registered under a specific domain."""
        return [
            tid for tid, caps in self.registry.items() if caps.domain == domain
        ]

    def get_capabilities(self, tid: str) -> Optional[TemplateCapabilities]:
        return self.registry.get(tid)


_registry = CapabilityRegistry()


def get_capability_registry() -> CapabilityRegistry:
    return _registry


def register_template_capabilities(
    tid: str,
    concepts: Set[str],
    composition_ready: bool = False,
    duration: float = 5.0,
    name: str = "",
    description: str = "",
    domain: str = "general",
):
    get_capability_registry().register(
        TemplateCapabilities(
            template_id=tid,
            name=name or tid.replace("_", " ").title(),
            description=description,
            concepts=concepts,
            composition_ready=composition_ready,
            estimated_duration=duration,
            domain=domain,
        )
    )


def initialize_all_capabilities():
    # ── Trigonometry ──────────────────────────────────────────────────────────
    register_template_capabilities(
        "unit_circle", {"unit circle", "sine", "cosine", "trigonometry", "trig"},
        True, 8.0, description="Params: color_cos, color_sin, run_time.", domain="trigonometry",
    )
    register_template_capabilities(
        "trig_waves", {"trig waves", "sine wave", "cosine wave", "waves"},
        True, 6.0, description="Params: expression, color, run_time.", domain="trigonometry",
    )
    register_template_capabilities(
        "trig_comparison", {"trig comparison", "sine cosine compare"},
        True, 6.0, description="Compare sin/cos waves side by side.", domain="trigonometry",
    )

    # ── Calculus ──────────────────────────────────────────────────────────────
    register_template_capabilities(
        "derivative_tangent", {"derivative", "tangent line", "slope of a curve"},
        True, 7.0, description="Tangent line approaching derivative.", domain="calculus",
    )
    register_template_capabilities(
        "derivative_slope", {"derivative", "tangent", "slope", "f prime"},
        True, 7.0, description="Derivative as slope of tangent line.", domain="calculus",
    )
    register_template_capabilities(
        "integral_area", {"integral", "area under curve"},
        True, 8.0, description="Area under curve visualization.", domain="calculus",
    )
    register_template_capabilities(
        "integral_accumulation", {"integral", "accumulation", "riemann sum", "area"},
        True, 8.0, description="Riemann sums accumulating to ∫f(x)dx.", domain="calculus",
    )
    register_template_capabilities(
        "chain_rule", {"chain rule", "composite function", "differentiation"},
        True, 7.0, description="Chain rule step-by-step.", domain="calculus",
    )
    register_template_capabilities(
        "gradient_descent", {"gradient descent", "optimization", "learning rate"},
        True, 8.0, description="Gradient descent steps on a loss surface.", domain="calculus",
    )
    register_template_capabilities(
        "gradient_descent_advanced", {"gradient descent", "gradient", "optimization", "loss"},
        True, 10.0, description="Advanced gradient descent with contour plots.", domain="calculus",
    )
    register_template_capabilities(
        "power_rule", {"power rule", "exponent", "derivative rule"},
        True, 5.0, description="Power rule derivation.", domain="calculus",
    )
    register_template_capabilities(
        "taylor_series", {"taylor series", "series approximation", "polynomial approximation"},
        True, 8.0, description="Taylor series polynomial approximation.", domain="calculus",
    )

    # ── Linear Algebra ────────────────────────────────────────────────────────
    register_template_capabilities(
        "matrix_multiplication", {"matrix multiplication", "dot product", "matrix product"},
        True, 8.0, description="Step-by-step dot product with row/column highlighting.", domain="linear_algebra",
    )
    register_template_capabilities(
        "matrix_multiplication_composition", {"matrix multiplication", "matrix composition"},
        True, 8.0, description="Composed matrix multiplication.", domain="linear_algebra",
    )
    register_template_capabilities(
        "vector_transformation", {"vector transformation", "linear transformation", "linear map"},
        True, 7.0, description="Vector space transformation visualization.", domain="linear_algebra",
    )
    register_template_capabilities(
        "eigenvector", {"eigenvector", "eigenvalue", "eigen"},
        True, 8.0, description="Eigenvector and eigenvalue basic visualization.", domain="linear_algebra",
    )
    register_template_capabilities(
        "eigenvector_composition", {"eigenvector", "eigenvalue", "stable direction"},
        True, 9.0, description="Composed eigenvector visualization.", domain="linear_algebra",
    )
    register_template_capabilities(
        "dot_product", {"dot product", "inner product", "projection"},
        True, 6.0, description="Dot product geometric interpretation.", domain="linear_algebra",
    )
    register_template_capabilities(
        "basis_change", {"basis change", "change of basis", "coordinate system"},
        True, 7.0, description="Change of basis visualization.", domain="linear_algebra",
    )

    # ── Machine Learning ──────────────────────────────────────────────────────
    register_template_capabilities(
        "neural_network", {"neural network", "deep learning", "layers", "neurons"},
        True, 8.0, description="Neural network architecture animation.", domain="ml",
    )
    register_template_capabilities(
        "transformer_attention", {"transformer", "attention mechanism", "self-attention"},
        True, 10.0, description="Transformer attention head visualization.", domain="ml",
    )
    register_template_capabilities(
        "backpropagation", {"backpropagation", "backprop", "gradient flow"},
        True, 10.0, description="Backpropagation gradient flow through network.", domain="ml",
    )
    register_template_capabilities(
        "embedding_space", {"embeddings", "latent space", "word vectors", "representation"},
        True, 8.0, description="Embedding space and clustering.", domain="ml",
    )
    register_template_capabilities(
        "convolution_filters", {"convolution", "cnn", "filter", "feature map"},
        True, 8.0, description="CNN convolution filter sliding across image.", domain="ml",
    )

    # ── Algorithms ────────────────────────────────────────────────────────────
    register_template_capabilities(
        "bfs_traversal", {"bfs", "breadth first search", "breadth-first", "graph traversal"},
        True, 8.0, description="BFS traversal animation on a graph.", domain="algorithms",
    )
    register_template_capabilities(
        "dfs_traversal", {"dfs", "depth first search", "depth-first", "graph traversal"},
        True, 8.0, description="DFS traversal animation on a graph.", domain="algorithms",
    )
    register_template_capabilities(
        "dijkstra", {"dijkstra", "shortest path", "weighted graph"},
        True, 9.0, description="Dijkstra shortest path relaxation steps.", domain="algorithms",
    )
    register_template_capabilities(
        "topological_sort", {"topological sort", "dag", "dependency ordering"},
        True, 8.0, description="Topological sort on a DAG.", domain="algorithms",
    )
    register_template_capabilities(
        "binary_search_tree", {"bst", "binary search tree", "tree", "insertion", "search"},
        True, 10.0, description="Visualize BST with insertion and search operations.", domain="algorithms",
    )
    register_template_capabilities(
        "graph_visualization", {"graph", "nodes", "edges", "traverse", "search"},
        True, 7.0, description="General graph visualization.", domain="algorithms",
    )

    # ── Primitives (composition building blocks) ──────────────────────────────
    register_template_capabilities(
        "draw_curve", {"curve", "graph", "function", "comparison"},
        True, 2.0, description="Params: expression, color, label, object_id.", domain="general",
    )
    register_template_capabilities(
        "draw_axis", {"axes", "coordinate axes", "axis"},
        True, 2.0, description="Draw coordinate axes.", domain="general",
    )
    register_template_capabilities(
        "write_text", {"text", "label", "title"},
        True, 2.0, description="Write text to screen.", domain="general",
    )
    register_template_capabilities(
        "place_point", {"point", "coordinate point"},
        True, 1.5, description="Place a labeled point.", domain="general",
    )
    register_template_capabilities(
        "draw_arrow", {"arrow", "direction", "vector arrow"},
        True, 1.5, description="Draw a directed arrow.", domain="general",
    )
    register_template_capabilities(
        "create_vector", {"vector", "2d vector", "direction"},
        True, 2.0, description="Animate a vector from origin.", domain="general",
    )
    register_template_capabilities(
        "transform_object", {"transform", "morph", "change shape"},
        True, 2.0, description="Transform one object into another.", domain="general",
    )
    register_template_capabilities(
        "highlight_object", {"highlight", "emphasize", "focus"},
        True, 1.5, description="Highlight an existing object.", domain="general",
    )
