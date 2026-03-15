from typing import Any, ClassVar, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)

class AnimationObject(BaseModel):
    """Primitive object in a scene."""
    id: str
    type: str  # axis, vector, matrix, graph, node, edge, token, circle, rectangle, line, curve, surface, text
    parameters: Dict[str, Any] = Field(default_factory=dict)

class AnimationStep(BaseModel):
    """Single animation action with optional duration."""
    object_id: str
    action: str  # fade_in, draw, grow, highlight, move, transform, connect, rotate, scale
    parameters: Dict[str, Any] = Field(default_factory=dict)
    duration: float = Field(default=1.0, description="Duration in seconds")
    
    # Animation duration heuristics (seconds)
    DURATION_MAP: ClassVar[Dict[str, float]] = {
        "fade_in": 0.5,
        "fade_out": 0.5,
        "write": 2.0,
        "draw": 2.0,
        "create": 1.5,
        "grow": 1.5,
        "shrink": 1.0,
        "move": 1.5,
        "transform": 2.0,
        "highlight": 1.0,
        "indicate": 1.0,
        "rotate": 1.5,
        "scale": 1.5,
        "color": 1.0,
        "connect": 1.5,
    }
    
    def estimate_duration(self) -> float:
        """Estimate duration based on action type."""
        return self.DURATION_MAP.get(self.action, 1.0)

class AnimationScene(BaseModel):
    """A sequence of objects and animations representing one explanation step with Scene Graph support."""
    scene_id: str
    description: Optional[str] = None
    template: Optional[str] = "generic"
    templates: List[str] = Field(default_factory=list, description="List of micro-templates to compose (composition mode)")
    depends_on: List[str] = Field(default_factory=list, description="Scene IDs that must be rendered before this one (scene graph)")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    objects: List[AnimationObject] = Field(default_factory=list)
    animations: List[AnimationStep] = Field(default_factory=list)
    narration: Optional[str] = None  # Voice-over text for the scene
    duration: float = Field(default=0.0, description="Scene duration in seconds (0 = auto-estimate)")
    output_objects: List[str] = Field(default_factory=list, description="Objects created by this scene that are available to next scenes")
    
    def calculate_estimated_duration(self) -> float:
        """
        Estimate total scene duration based on animations.
        
        Returns:
            Estimated duration in seconds
        """
        if not self.animations:
            return 2.0  # Default minimum for setup
        
        total = sum(step.estimate_duration() for step in self.animations)
        # Add buffer for setup and teardown
        total += 1.0
        return total
    
    def get_effective_duration(self) -> float:
        """
        Get the scene duration, auto-estimating if not specified.
        
        Returns:
            Duration in seconds (either specified or estimated)
        """
        if self.duration > 0:
            return self.duration
        return self.calculate_estimated_duration()
    
    @field_validator('depends_on')
    def validate_depends_on(cls, v):
        """Ensure depends_on only references existing scenes."""
        if not isinstance(v, list):
            raise ValueError("depends_on must be a list")
        return v
    
    @field_validator('templates')
    def validate_templates(cls, v):
        """Ensure templates list is not empty when using composition mode."""
        if v and not isinstance(v, list):
            raise ValueError("templates must be a list")
        return v
    
    def estimate_narration_duration(self) -> float:
        """
        Estimate narration duration based on word count.
        
        Assuming ~140 words per minute (typical speaking rate).
        """
        if not self.narration:
            return 0.0
        
        words = len(self.narration.split())
        # 140 WPM = ~2.33 seconds per 10 words
        return (words / 140.0) * 60.0

class AnimationPlan(BaseModel):
    """Structured animation plan (DSL) with Scene Graph support."""
    title: str
    template: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    scenes: List[AnimationScene] = Field(default_factory=list)
    rate_limited: bool = Field(default=False, description="True if this plan was generated under quota limits")
    
    def validate_scene_dependencies(self) -> List[str]:
        """
        Validate that scene dependencies are acyclic and reference existing scenes.
        Returns a list of validation errors (empty if valid).
        """
        errors = []
        scene_ids = {s.scene_id for s in self.scenes}
        
        # Check that all dependencies reference existing scenes
        for scene in self.scenes:
            for dep in scene.depends_on:
                if dep not in scene_ids:
                    errors.append(f"Scene '{scene.scene_id}' depends on non-existent scene '{dep}'")
        
        # Check for cycles (basic cycle detection)
        visited = set()
        rec_stack = set()
        
        def has_cycle(scene_id, graph):
            visited.add(scene_id)
            rec_stack.add(scene_id)
            
            for neighbor in graph.get(scene_id, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, graph):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(scene_id)
            return False
        
        # Build dependency graph
        graph = {s.scene_id: s.depends_on for s in self.scenes}
        for scene_id in scene_ids:
            if scene_id not in visited:
                if has_cycle(scene_id, graph):
                    errors.append(f"Circular dependency detected involving scene '{scene_id}'")
        
        return errors
    
    def topological_sort_scenes(self) -> List[AnimationScene]:
        """
        Return scenes in topological order based on dependencies.
        """
        errors = self.validate_scene_dependencies()
        if errors:
            raise ValueError(f"Scene dependency validation failed: {errors}")
        
        scene_map = {s.scene_id: s for s in self.scenes}
        visited = set()
        result = []
        
        def visit(scene_id):
            if scene_id in visited:
                return
            visited.add(scene_id)
            scene = scene_map[scene_id]
            for dep in scene.depends_on:
                visit(dep)
            result.append(scene)
        
        for scene in self.scenes:
            visit(scene.scene_id)
        
        return result
    
    def calculate_total_duration(self) -> float:
        """
        Calculate total animation duration including all scenes.
        
        Returns:
            Duration in seconds
        """
        # Sort by dependencies first
        sorted_scenes = self.topological_sort_scenes()
        
        total = 0.0
        for scene in sorted_scenes:
            scene_duration = scene.get_effective_duration()
            # Narration might be longer than animation
            narration_duration = scene.estimate_narration_duration()
            # Take the maximum
            total += max(scene_duration, narration_duration)
        
        return total
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get comprehensive metadata about the animation plan.
        
        Returns:
            Dict with title, total_duration, scene_count, etc.
        """
        sorted_scenes = self.topological_sort_scenes()
        return {
            "title": self.title,
            "total_scenes": len(self.scenes),
            "total_duration": self.calculate_total_duration(),
            "average_scene_duration": self.calculate_total_duration() / len(self.scenes) if self.scenes else 0,
            "narration_lines": sum(1 for s in self.scenes if s.narration),
            "composition_enabled": sum(1 for s in self.scenes if s.templates),
            "execution_order": [s.scene_id for s in sorted_scenes],
        }

    @classmethod
    def create_fallback(cls, prompt: str = "Simple Animation") -> "AnimationPlan":
        """Create a minimal fallback animation plan."""
        return cls(
            title=prompt[:60],
            scenes=[
                AnimationScene(
                    scene_id="fallback",
                    objects=[AnimationObject(id="text", type="text", parameters={"text": "Hello World"})],
                    animations=[AnimationStep(object_id="text", action="write", duration=2.0)],
                    narration="Starting fallback animation",
                    duration=3.0
                )
            ]
        )

    @classmethod
    def create_rate_limited_fallback(cls, prompt: str = "Rate limit reached") -> "AnimationPlan":
        """Plan returned when LLM quota is exceeded.

        The scene gently tells the user to simplify their prompt or wait for quota
        renewal. Duration is short to minimize resource usage.
        """
        return cls(
            title="Rate Limited",
            rate_limited=True,
            scenes=[
                AnimationScene(
                    scene_id="rate_limit",
                    objects=[AnimationObject(id="text", type="text", parameters={"text": "Please simplify your request or try again later."})],
                    animations=[AnimationStep(object_id="text", action="write", duration=2.0)],
                    narration="The LLM quota has been exceeded. Please reduce complexity or upgrade.",
                    duration=4.0
                )
            ]
        )
