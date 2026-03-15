"""Template capability metadata and intelligent routing system."""

from typing import Set, Dict, List, Type, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class TemplateCapabilities:
    """Metadata describing what a template can visualize."""
    template_id: str
    name: str
    description: str
    concepts: Set[str] = field(default_factory=set)  # Concepts it can explain
    requirements: Set[str] = field(default_factory=set)  # Required inputs/context
    composition_ready: bool = False  # Can work in composition mode
    estimated_duration: float = 5.0  # Typical scene duration in seconds
    
    def matches_concept(self, concept: str) -> float:
        """
        Return match score (0-1) for a concept.
        
        This enables the router to rank templates by relevance.
        """
        if concept.lower() in [c.lower() for c in self.concepts]:
            return 1.0
        
        # Fuzzy matching for partial matches
        concept_lower = concept.lower()
        for c in self.concepts:
            if concept_lower in c.lower() or c.lower() in concept_lower:
                return 0.7
        
        return 0.0
    
    def can_chain_with(self, other: "TemplateCapabilities") -> bool:
        """Check if this template can follow another in composition."""
        # Templates are compatible if:
        # 1. This template's requirements are satisfied by the other's outputs
        # 2. No conflicting concepts
        return True  # For now, allow all chains (can restrict later)


class CapabilityRegistry:
    """Central registry of template capabilities."""
    
    def __init__(self):
        self.registry: Dict[str, TemplateCapabilities] = {}
    
    def register(self, capabilities: TemplateCapabilities) -> None:
        """Register a template's capabilities."""
        self.registry[capabilities.template_id] = capabilities
        logger.debug(f"Registered template: {capabilities.template_id}")
    
    def find_templates_for_concept(self, concept: str, 
                                    composition_mode: bool = False) -> List[str]:
        """
        Find templates that can explain a concept, ranked by relevance.
        
        Args:
            concept: The concept to explain
            composition_mode: If True, only return composition-ready templates
        
        Returns:
            List of template IDs ranked by match score (descending)
        """
        matches = []
        
        for template_id, caps in self.registry.items():
            if composition_mode and not caps.composition_ready:
                continue
            
            score = caps.matches_concept(concept)
            if score > 0:
                matches.append((template_id, score))
        
        # Sort by score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        return [template_id for template_id, _ in matches]
    
    def get_capabilities(self, template_id: str) -> Optional[TemplateCapabilities]:
        """Get capabilities for a specific template."""
        return self.registry.get(template_id)
    
    def validate_template_exists(self, template_id: str) -> bool:
        """Check if a template is registered."""
        return template_id in self.registry
    
    def get_composition_chain(self, concept: str, num_templates: int = 3) -> List[str]:
        """
        Get a recommended chain of composition templates for a concept.
        
        Example:
            concept: "eigenvectors"
            Returns: ["draw_axis", "create_vector", "transform_object"]
        """
        templates = self.find_templates_for_concept(concept, composition_mode=True)
        return templates[:num_templates]


# Global registry instance
_capability_registry = CapabilityRegistry()


def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry."""
    return _capability_registry


def register_template_capabilities(template_id: str, concepts: Set[str], 
                                   composition_ready: bool = False,
                                   duration: float = 5.0,
                                   name: str = "",
                                   description: str = "") -> None:
    """
    Helper function to register template capabilities.
    
    Usage:
        register_template_capabilities(
            "eigenvectors_advanced",
            concepts={"eigenvectors", "linear_transformation", "eigenvalues"},
            composition_ready=True,
            duration=8.0
        )
    """
    registry = get_capability_registry()
    caps = TemplateCapabilities(
        template_id=template_id,
        name=name or template_id.replace("_", " ").title(),
        description=description,
        concepts=concepts,
        composition_ready=composition_ready,
        estimated_duration=duration
    )
    registry.register(caps)


def initialize_all_capabilities() -> None:
    """Initialize capabilities for all known templates."""
    registry = get_capability_registry()
    
    # Linear Algebra Templates
    register_template_capabilities(
        "eigenvectors_advanced",
        concepts={"eigenvectors", "eigenvalues", "linear transformation", "stable direction"},
        composition_ready=True,
        duration=8.0,
        name="Eigenvectors Visualization"
    )
    
    register_template_capabilities(
        "vector_projection",
        concepts={"projection", "dot product", "vector decomposition", "orthogonal"},
        composition_ready=True,
        duration=6.0,
        name="Vector Projection"
    )
    
    register_template_capabilities(
        "basis_change",
        concepts={"basis", "transformation", "change of basis", "coordinate systems"},
        composition_ready=True,
        duration=7.0,
        name="Basis Change"
    )
    
    register_template_capabilities(
        "matrix_multiplication",
        concepts={"matrix multiplication", "matrix product", "linear algebra"},
        composition_ready=False,
        duration=5.0
    )
    
    # Calculus Templates
    register_template_capabilities(
        "derivative_slope",
        concepts={"derivative", "slope", "tangent line", "rate of change"},
        composition_ready=True,
        duration=6.0,
        name="Derivative as Slope"
    )
    
    register_template_capabilities(
        "integral_accumulation",
        concepts={"integral", "accumulation", "area under curve", "antiderivative"},
        composition_ready=True,
        duration=7.0,
        name="Integral Accumulation"
    )
    
    register_template_capabilities(
        "chain_rule",
        concepts={"chain rule", "composition", "function composition", "calculus"},
        composition_ready=True,
        duration=7.0,
        name="Chain Rule"
    )
    
    register_template_capabilities(
        "gradient_descent_advanced",
        concepts={"gradient descent", "optimization", "learning rate", "convergence"},
        composition_ready=True,
        duration=8.0,
        name="Gradient Descent"
    )
    
    # Algorithm Templates
    register_template_capabilities(
        "bfs_traversal",
        concepts={"BFS", "breadth first search", "graph traversal", "shortest path"},
        composition_ready=False,
        duration=6.0,
        name="BFS Traversal"
    )
    
    register_template_capabilities(
        "dfs_traversal",
        concepts={"DFS", "depth first search", "graph traversal", "backtracking"},
        composition_ready=True,
        duration=6.0,
        name="DFS Traversal"
    )
    
    register_template_capabilities(
        "dijkstra",
        concepts={"Dijkstra", "shortest path", "weighted graph", "pathfinding"},
        composition_ready=True,
        duration=8.0,
        name="Dijkstra's Algorithm"
    )
    
    register_template_capabilities(
        "topological_sort",
        concepts={"topological sort", "DAG", "dependency graph", "task ordering"},
        composition_ready=True,
        duration=6.0,
        name="Topological Sort"
    )
    
    register_template_capabilities(
        "graph_visualization",
        concepts={"graph", "nodes", "edges", "network", "structure"},
        composition_ready=True,
        duration=5.0,
        name="Graph Visualization"
    )
    
    # Machine Learning Templates
    register_template_capabilities(
        "backpropagation",
        concepts={"backpropagation", "gradient flow", "neural network training", "weight updates"},
        composition_ready=True,
        duration=8.0,
        name="Backpropagation"
    )
    
    register_template_capabilities(
        "embedding_spaces",
        concepts={"embeddings", "latent space", "semantic space", "word vectors"},
        composition_ready=True,
        duration=7.0,
        name="Embedding Spaces"
    )
    
    register_template_capabilities(
        "convolution_filters",
        concepts={"convolution", "CNN", "feature maps", "filters", "kernels"},
        composition_ready=True,
        duration=7.0,
        name="Convolution Filters"
    )
    
    register_template_capabilities(
        "neural_network",
        concepts={"neural network", "layers", "nodes", "connections", "architecture"},
        composition_ready=False,
        duration=6.0,
        name="Neural Network"
    )
    
    register_template_capabilities(
        "transformer_attention",
        concepts={"transformer", "attention mechanism", "self-attention", "sequence modeling"},
        composition_ready=False,
        duration=8.0,
        name="Transformer Attention"
    )
    
    # Micro-templates (Primitives)
    register_template_capabilities(
        "draw_curve",
        concepts={"curve", "function", "graph", "mathematical function"},
        composition_ready=True,
        duration=2.0,
        name="Draw Curve"
    )
    
    register_template_capabilities(
        "place_point",
        concepts={"point", "coordinate", "location", "position"},
        composition_ready=True,
        duration=1.5,
        name="Place Point"
    )
    
    register_template_capabilities(
        "draw_arrow",
        concepts={"arrow", "direction", "vector", "indicator"},
        composition_ready=True,
        duration=1.5,
        name="Draw Arrow"
    )
    
    register_template_capabilities(
        "draw_axis",
        concepts={"axis", "coordinate system", "axes", "grid"},
        composition_ready=True,
        duration=2.0,
        name="Draw Axis"
    )
    
    register_template_capabilities(
        "write_text",
        concepts={"text", "label", "annotation", "explanation"},
        composition_ready=True,
        duration=2.0,
        name="Write Text"
    )
    
    register_template_capabilities(
        "create_vector",
        concepts={"vector", "arrow", "magnitude", "direction"},
        composition_ready=True,
        duration=2.0,
        name="Create Vector"
    )
    
    register_template_capabilities(
        "highlight_object",
        concepts={"highlight", "emphasis", "focus", "attention"},
        composition_ready=True,
        duration=1.0,
        name="Highlight Object"
    )
    
    register_template_capabilities(
        "transform_object",
        concepts={"transform", "animation", "change", "motion"},
        composition_ready=True,
        duration=2.0,
        name="Transform Object"
    )
    
    logger.info(f"Initialized {len(registry.registry)} template capabilities")
