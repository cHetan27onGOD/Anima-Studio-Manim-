"""Phase 3: Narration Generation Engine

Generates voice-over scripts based on animation plans and concepts.
This is the foundation for automatic educational video creation.

Pipeline:
    AnimationPlan → Scene Analysis → Concept Expansion → 
    Narration Generation → Voice Synthesis
"""

from typing import List, Dict, Optional, Any
import logging
from app.schemas.animation import AnimationPlan, AnimationScene
from app.templates.capabilities import get_capability_registry

logger = logging.getLogger(__name__)


class NarrationGenerator:
    """
    Generates narration scripts for animation scenes.
    
    Strategies:
    1. Use LLM to generate narration based on scene context
    2. Use templates for common patterns
    3. Incorporate concept explanations from capability registry
    """
    
    # Template narrations for common educational patterns
    PATTERN_TEMPLATES = {
        "introduction": "Let's explore the concept of {concept}.",
        "vector_visualization": "Here we see {concept}. The {detail} is represented by {representation}.",
        "transformation": "Now we apply a transformation. Notice how {observation}.",
        "comparison": "Compare this to {comparison}. The key difference is {difference}.",
        "conclusion": "As we can see, {concept} helps us understand {application}.",
        "intuition": "Intuitively, {concept} means {meaning}.",
        "mechanism": "The mechanism works as follows: {steps}.",
        "result": "The final result shows that {result}.",
    }
    
    def __init__(self):
        self.registry = get_capability_registry()
    
    def generate_narration_for_scene(
        self,
        scene: AnimationScene,
        concept: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate narration for a single scene.
        
        Args:
            scene: The animation scene
            concept: Optional concept being explained
            context: Additional context (previous scenes, etc.)
        
        Returns:
            Narration string
        """
        # If scene already has narration, return it
        if scene.narration:
            return scene.narration
        
        # Try to infer narration from scene structure
        return self._infer_narration_from_scene(scene, concept, context)
    
    def _infer_narration_from_scene(
        self,
        scene: AnimationScene,
        concept: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Attempt to infer narration from scene structure."""
        
        # Pattern 1: Scene has a single domain template
        if scene.template and scene.template != "generic":
            caps = self.registry.get_capabilities(scene.template)
            if caps:
                return f"Now we examine {caps.name.lower()}. "
        
        # Pattern 2: Scene uses composition
        if scene.templates:
            template_names = " and ".join(
                self.registry.get_capabilities(t).name.lower() 
                for t in scene.templates if self.registry.get_capabilities(t)
            )
            return f"Building up the visualization: {template_names}. "
        
        # Pattern 3: Use scene description
        if scene.description:
            return f"{scene.description}. "
        
        # Pattern 4: Fallback to generic
        return "Let's examine the next step of the animation. "
    
    def generate_narration_plan(
        self,
        plan: AnimationPlan,
        fill_missing_only: bool = True
    ) -> AnimationPlan:
        """
        Generate narration for all scenes in a plan.
        
        Args:
            plan: The animation plan
            fill_missing_only: If True, only generate for scenes without narration
        
        Returns:
            Updated plan with narration
        """
        concept = self._extract_concept_from_plan(plan)
        
        for scene in plan.scenes:
            if not fill_missing_only or not scene.narration:
                narration = self.generate_narration_for_scene(
                    scene,
                    concept=concept
                )
                scene.narration = narration
                logger.debug(f"Generated narration for {scene.scene_id}")
        
        return plan
    
    def _extract_concept_from_plan(self, plan: AnimationPlan) -> Optional[str]:
        """Extract the main concept from a plan's title or template."""
        # Try to get from title
        title = plan.title.lower()
        
        # Common patterns
        patterns = [
            "explain", "visualize", "demonstrate",
            "show", "understanding", "introduction"
        ]
        
        # Extract key words
        for scene in plan.scenes:
            if scene.template and scene.template != "generic":
                caps = self.registry.get_capabilities(scene.template)
                if caps and caps.concepts:
                    return list(caps.concepts)[0]
        
        return None


class NarrationDurationCalculator:
    """
    Calculate narration durations to sync with animations.
    
    Standard speaking rates:
    - Slow: ~100 WPM
    - Normal: ~140 WPM
    - Fast: ~180 WPM
    """
    
    NORMAL_WPM = 140
    SLOW_WPM = 100
    FAST_WPM = 180
    
    @staticmethod
    def estimate_duration(text: str, rate: str = "normal") -> float:
        """
        Estimate narration duration in seconds.
        
        Args:
            text: The narration text
            rate: "slow", "normal", or "fast"
        
        Returns:
            Duration in seconds
        """
        if not text:
            return 0.0
        
        words = len(text.split())
        
        wpm_map = {
            "slow": NarrationDurationCalculator.SLOW_WPM,
            "normal": NarrationDurationCalculator.NORMAL_WPM,
            "fast": NarrationDurationCalculator.FAST_WPM,
        }
        
        wpm = wpm_map.get(rate, NarrationDurationCalculator.NORMAL_WPM)
        return (words / wpm) * 60.0  # Convert to seconds
    
    @staticmethod
    def sync_scene_duration(scene: AnimationScene, rate: str = "normal") -> float:
        """
        Get the duration a scene should be based on narration.
        
        Returns:
            Duration in seconds (max of scene duration and narration duration)
        """
        if not scene.narration:
            return scene.get_effective_duration()
        
        narration_duration = NarrationDurationCalculator.estimate_duration(
            scene.narration,
            rate=rate
        )
        
        animation_duration = scene.get_effective_duration()
        
        # Return the maximum to ensure both animation and narration complete
        return max(animation_duration, narration_duration)


class ConceptExpander:
    """
    Expand a concept into a sequence of explanatory scenes.
    
    This enables automatic generation of multi-step explanations.
    """
    
    def __init__(self):
        self.registry = get_capability_registry()
    
    def expand_concept(self, concept: str, max_scenes: int = 5) -> List[str]:
        """
        Find related templates that can build up an explanation.
        
        Example:
            concept: "eigenvectors"
            Returns: [
                "vector_space",      # Context
                "linear_transformation",  # Foundation
                "eigenvectors_advanced",  # Main concept
                "stable_direction"    # Insight
            ]
        
        Args:
            concept: Main concept to explain
            max_scenes: Maximum number of scenes to generate
        
        Returns:
            List of template IDs in pedagogical order
        """
        templates = self.registry.find_templates_for_concept(concept)
        
        # Prioritize:
        # 1. Prerequisite concepts (e.g., vectors before eigenvectors)
        # 2. The main template
        # 3. Related deepening concepts
        
        ordered = []
        
        # Add primitives for setup
        if "draw_axis" not in templates:
            ordered.append("draw_axis")
        if "create_vector" not in templates:
            ordered.append("create_vector")
        
        # Add main templates
        ordered.extend(templates)
        
        # Return up to max_scenes
        return ordered[:max_scenes]


class NarrationPipeline:
    """
    Complete pipeline for generating narration and syncing with animation.
    
    Flow:
        AnimationPlan
        ↓
        NarrationGenerator (fill missing narration)
        ↓
        NarrationDurationCalculator (sync timings)
        ↓
        Output: Annotated plan with narration + durations
    """
    
    def __init__(self):
        self.narrator = NarrationGenerator()
        self.duration_calculator = NarrationDurationCalculator()
        self.concept_expander = ConceptExpander()
    
    def process_plan(self, plan: AnimationPlan) -> AnimationPlan:
        """
        Process a plan through the complete narration pipeline.
        
        Args:
            plan: Animation plan (some scenes may have narration)
        
        Returns:
            Plan with complete narration and synced durations
        """
        # Step 1: Generate missing narration
        logger.info("Step 1: Generating narration...")
        plan = self.narrator.generate_narration_plan(plan, fill_missing_only=True)
        
        # Step 2: Sync scene durations to narration
        logger.info("Step 2: Syncing scene durations...")
        for scene in plan.scenes:
            synced_duration = self.duration_calculator.sync_scene_duration(scene)
            if scene.duration == 0:  # Only update if auto-estimate
                scene.duration = synced_duration
        
        # Step 3: Calculate total duration
        total_duration = plan.calculate_total_duration()
        logger.info(f"Step 3: Total animation duration: {total_duration:.1f}s")
        
        return plan
    
    def suggest_expansion(
        self,
        concept: str,
        num_scenes: int = 4
    ) -> Dict[str, Any]:
        """
        Suggest a scene expansion for a concept.
        
        Useful for the LLM planner to generate better plans.
        
        Args:
            concept: Main concept
            num_scenes: Desired number of scenes
        
        Returns:
            Dict with suggested templates and narration patterns
        """
        templates = self.concept_expander.expand_concept(concept, max_scenes=num_scenes)
        
        suggestions = {
            "concept": concept,
            "suggested_scenes": [],
            "total_estimated_duration": 0.0
        }
        
        for i, template_id in enumerate(templates):
            caps = self.registry.get_capabilities(template_id)
            if caps:
                suggestions["suggested_scenes"].append({
                    "scene_id": f"scene_{i}",
                    "template": template_id,
                    "expected_duration": caps.estimated_duration,
                    "description": caps.description,
                    "concepts": list(caps.concepts),
                })
                suggestions["total_estimated_duration"] += caps.estimated_duration
        
        return suggestions
