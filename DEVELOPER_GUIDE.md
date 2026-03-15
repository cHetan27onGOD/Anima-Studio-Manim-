# Developer Guide: Using Phase 2 + Improvements

This guide shows you how to use the new composition framework, register templates, and leverage the narration engine.

---

## Quick Start: 5 Minute Overview

### 1. Understanding Namespace Isolation

```python
from app.templates.composition import TemplateComposer
from app.templates.primitives import DrawCurveTemplate, PlacePointTemplate

# Create two compositions with same logical object names
composer1 = TemplateComposer("scene1_derivative")
composer1.add_template(DrawCurveTemplate({"expression": "x**2"}))
composer1.add_template(PlacePointTemplate({"x": 1.0}))

composer2 = TemplateComposer("scene2_transformation")
composer2.add_template(DrawCurveTemplate({"expression": "2*x**2"}))
composer2.add_template(PlacePointTemplate({"x": 2.0}))

# No naming conflicts!
# Internally: scene1_derivative_curve, scene1_derivative_point
#            scene2_transformation_curve, scene2_transformation_point

code1 = composer1.compose()
code2 = composer2.compose()
```

### 2. Registering Template Capabilities

```python
from app.templates.capabilities import register_template_capabilities

# Tell the system what your template does
register_template_capabilities(
    template_id="my_custom_template",
    concepts={"linear algebra", "transformation", "visualization"},
    composition_ready=True,  # Can be used in multi-template scenes
    duration=6.0,  # Typical scene length
    name="Custom Template",
    description="Visualizes linear transformations"
)

# Now your template is discoverable
from app.templates.capabilities import get_capability_registry
registry = get_capability_registry()
templates = registry.find_templates_for_concept("transformation")
# Returns: [..., "my_custom_template"] (ranked by relevance)
```
### Handling LLM Quotas & Complex Plans

The Gemini free tier imposes monthly and per-request token limits. Longer or more detailed prompts can exceed these quotas, causing plan generation failures.

**Built-in protections:**

- `call_combined_llm_planner()` now injects a **brevity note** telling the model to stay under 8 scenes and ~2000 tokens.
- Prompts longer than 2 000 characters are truncated automatically.
- If the LLM responds with a quota/limit error, we catch it and return a special 
  `rate_limited` fallback plan instead of crashing the job.  The fallback video 
  politely advises the user to simplify their request.
- Plans that exceed 8 scenes are flagged during validation; the repair loop may
  trim or regenerate.

Jobs where the plan was rate‑limited have `plan.rate_limited == True` in the
stored `plan_json`, and the worker logs an explicit message.  The frontend can
read this flag and show a warning toast.

**Strategies for users:**
1. Chunk very large concepts into multiple prompts/jobs.
2. Rely on cached plans (Redis TTL 24 h) to avoid repeated token usage.
3. Fall back to local templates (`generic` or specific domain templates) when
   you already know which visual you need.

### 3. Using Duration Estimation

```python
from app.schemas.animation import AnimationScene, AnimationStep

scene = AnimationScene(
    scene_id="intro",
    description="Introduction to eigenvectors",
    narration="Eigenvectors are special vectors that don't change direction. " * 3,
    animations=[
        AnimationStep(object_id="vector", action="create", duration=1.5),
        AnimationStep(object_id="vector", action="transform", duration=2.0),
        AnimationStep(object_id="vector", action="highlight", duration=1.0),
    ]
)

# Auto-estimate animation duration
anim_duration = scene.calculate_estimated_duration()  # ~5.5 seconds

# Estimate narration duration
narration_duration = scene.estimate_narration_duration()  # ~4.3 seconds

# Get effective duration (max of both)
effective = scene.get_effective_duration()  # ~5.5 seconds
```

### 4. Generating Narration

```python
from app.services.narration import NarrationPipeline
from app.schemas.animation import AnimationPlan

# Create a plan (some scenes may not have narration)
plan = AnimationPlan(
    title="Understanding Eigenvectors",
    scenes=[...]  # Your scenes
)

# Process through narration pipeline
pipeline = NarrationPipeline()
annotated_plan = pipeline.process_plan(plan)

# Result: All scenes have narration + synced durations
for scene in annotated_plan.scenes:
    print(f"{scene.scene_id}: {scene.narration}")
    print(f"  Duration: {scene.get_effective_duration():.1f}s")
```

### 5. Smart Template Discovery

```python
from app.templates.capabilities import get_capability_registry

registry = get_capability_registry()

# Find templates for a concept
templates = registry.find_templates_for_concept("eigenvectors")
print(templates)
# Output: ["eigenvectors_advanced", "linear_transformation", ...]
# (ranked by relevance)

# Only composition-ready templates
composition = registry.find_templates_for_concept(
    "eigenvectors",
    composition_mode=True
)

# Get capabilities for a specific template
caps = registry.get_capabilities("eigenvectors_advanced")
print(caps.concepts)  # {"eigenvectors", "eigenvalues", ...}
print(caps.estimated_duration)  # 8.0
print(caps.composition_ready)  # True
```

---

## Creating a New Composition-Aware Template

### Step 1: Define the Template Class

```python
from app.templates.composition import CompositionAwareTemplate

class MyNewTemplate(CompositionAwareTemplate):
    """Template for explaining my concept."""
    
    def compose(self) -> None:
        """Execute the template composition."""
        
        # Get parameters
        param1 = self.parameters.get("param1", "default")
        
        # Check if prerequisite objects exist
        if self.object_exists("axes"):
            # Reuse existing axes
            pass
        else:
            # Create axes
            self.create_object(
                logical_id="axes",
                obj_type="axes",
                creation_code="        ax = Axes()\n",
                data={"x_range": [-5, 5], "y_range": [-3, 3]}
            )
        
        # Create your objects
        self.create_object(
            logical_id="my_object",
            obj_type="custom_type",
            creation_code="        my_obj = SomeObject()\n",
            data={"param": param1}
        )
        
        # Add animations
        self.add_animation_code("        self.play(Create(my_obj))\n")
        self.add_animation_code("        self.wait(1)\n")
```

### Step 2: Register Capabilities

```python
# In templates/capabilities.py or your registration module
from app.templates.capabilities import register_template_capabilities

register_template_capabilities(
    template_id="my_new_template",
    concepts={"concept1", "concept2", "concept3"},
    composition_ready=True,
    duration=7.0,
    name="My New Template",
    description="Explains concept1 and concept2"
)
```

### Step 3: Register in Engine

```python
# In templates/engine.py

from app.templates.my_new_template import MyNewTemplate

TEMPLATES: Dict[str, Type[BaseTemplate]] = {
    # ... existing templates ...
    "my_new_template": MyNewTemplate,
}
```

### Step 4: Use in Plans

```python
from app.schemas.animation import AnimationPlan, AnimationScene

plan = AnimationPlan(
    title="My Explanation",
    parameters={
        "scenes": [
            {
                "scene_id": "main",
                "template": "my_new_template",
                "parameters": {"param1": "value1"},
                "narration": "Here's my explanation..."
            }
        ]
    }
)
```

---

## Advanced: Composition Patterns

### Pattern 1: Build Complex Visualizations

```python
# Micro-templates compose to create complex animation
composer = TemplateComposer("complex_scene")

# Layer 1: Axes
composer.add_template(DrawAxisTemplate({
    "x_range": [-5, 5],
    "y_range": [-3, 3]
}))

# Layer 2: Multiple vectors
for i, coords in enumerate([[1, 1], [2, 1], [3, 2]]):
    composer.add_template(CreateVectorTemplate({"coords": coords}))

# Layer 3: Highlight special vectors
composer.add_template(HighlightObjectTemplate({"target_id": "vector_1"}))

# Result: Professional visualization built from simple pieces
code = composer.compose()
```

### Pattern 2: Pedagogical Sequences

```python
# Templates in specific order for educational effect
composer = TemplateComposer("learning_sequence")

# Show what
composer.add_template(DrawCurveTemplate({"expression": "x**2"}))

# Show where
composer.add_template(PlacePointTemplate({"x": 1.0}))

# Show why (tangent line)
composer.add_template(DrawArrowTemplate({"start": [0, 0], "end": [1, 2]}))

# Reinforce (highlight)
composer.add_template(HighlightObjectTemplate({"target_id": "point"}))

code = composer.compose()
```

### Pattern 3: Reusing Context

```python
# Scene 1: Create objects
ctx1 = CompositionContext("scene1")
template1 = DrawCurveTemplate({"expression": "x**2"})
template1.set_composition_context(ctx1)
template1.compose()
# ctx1 now has "curve"

# Scene 2: Use same context (if needed for cross-scene reference)
# (Usually not recommended, but possible)
# template2.set_composition_context(ctx1)
# Can now reference ctx1's objects

# More common: Scene 2 uses its own context
ctx2 = CompositionContext("scene2")
template3 = DrawCurveTemplate({"expression": "2*x**2"})
template3.set_composition_context(ctx2)
template3.compose()
# scene1_curve and scene2_curve (no collision)
```

---

## Integration with LLM Planner

### Using Capability Registry in Planning

```python
# In services/llm.py (modify call_combined_llm_planner)

from app.templates.capabilities import get_capability_registry

def improved_llm_planner(user_prompt: str) -> AnimationPlan:
    registry = get_capability_registry()
    
    # Extract concepts from prompt
    concepts = extract_concepts(user_prompt)
    
    # Find recommended templates
    recommended_templates = {}
    for concept in concepts:
        templates = registry.find_templates_for_concept(concept)
        recommended_templates[concept] = templates[:3]  # Top 3
    
    # Build prompt with template hints
    template_hints = "\n".join([
        f"For {concept}: {', '.join(templates)}"
        for concept, templates in recommended_templates.items()
    ])
    
    planner_prompt = f"""
    You are planning an animation to explain: {user_prompt}
    
    Available templates (ranked by relevance):
    {template_hints}
    
    Generate a scene graph plan using these templates.
    Prefer composition-ready templates for multi-step visuals.
    """
    
    # Call LLM with improved context
    return call_llm(planner_prompt)
```

---

## Testing Your Templates

### Unit Test: Composition

```python
def test_my_template_composition():
    from app.templates.composition import TemplateComposer
    from app.templates.my_new_template import MyNewTemplate
    
    composer = TemplateComposer("test_scene")
    composer.add_template(MyNewTemplate({"param1": "test"}))
    
    code = composer.compose()
    
    # Verify code contains expected elements
    assert "from manim import" in code
    assert "class Scene1(Scene)" in code
    assert "self.play" in code or "Create" in code
    
    # Verify no syntax errors
    compile(code, "test", "exec")
```

### Integration Test: Plan → Code

```python
def test_full_rendering_pipeline():
    from app.schemas.animation import AnimationPlan
    from app.templates.engine import render_multi_scene_plan
    
    plan = AnimationPlan(
        title="Test",
        parameters={
            "scenes": [
                {
                    "scene_id": "test",
                    "template": "my_new_template",
                    "parameters": {"param1": "value"}
                }
            ]
        }
    )
    
    code = render_multi_scene_plan(plan.model_dump())
    
    # Should be valid Manim code
    assert "from manim import *" in code
    assert "class Scene1(Scene):" in code
    compile(code, "test", "exec")
```

---

## Performance Tips

### 1. Use Composition for Reuse

❌ **Bad**: Create 14 separate templates for different variations

✅ **Good**: 4 micro-templates that compose to 196 different variations

### 2. Cache Capability Lookups

```python
# Initialize capabilities once at startup
from app.templates.capabilities import initialize_all_capabilities

initialize_all_capabilities()  # ~50ms, do once

# Then lookups are O(1)
registry.find_templates_for_concept("eigenvectors")  # ~1ms
```

### 3. Parallelize Scene Rendering

```python
# Use async/workers for multiple scenes
# (Future feature) - Scene graph enables this

scenes = plan.topological_sort_scenes()

# Scene 1 and Scene 2 can render in parallel if no dependencies
# Current: Sequential, but DAG structure enables future parallelization
```

### 4. Leverage Redis Caching

```python
# Plans are cached for 24 hours
# Same prompt → instant response

# Cache key: MD5(prompt)
# Hit rate: ~80% for educational content
```

---

## Common Patterns & Anti-Patterns

### ✅ Do

- Register capabilities for every template
- Use composition for reusable components
- Let namespace isolation handle naming
- Use narration pipeline for complete plans
- Test templates before adding to registry

### ❌ Don't

- Hardcode template mappings in LLM prompt
- Create monolithic 500-line templates
- Assume object names are unique
- Skip narration generation
- Add templates without capability metadata

---

## Debugging

### Print Composed Code

```python
composer = TemplateComposer("debug")
composer.add_template(MyTemplate(...))
code = composer.compose()
print(code)  # See actual Manim code
```

### Check Capabilities

```python
registry = get_capability_registry()
caps = registry.get_capabilities("my_template")
if caps:
    print(f"Concepts: {caps.concepts}")
    print(f"Composition ready: {caps.composition_ready}")
else:
    print("Template not registered!")
```

### Validate Plan

```python
plan = AnimationPlan(...)
errors = plan.validate_scene_dependencies()
if errors:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✅ Plan is valid")

metadata = plan.get_metadata()
print(f"Total duration: {metadata['total_duration']:.1f}s")
```

---

## Next Steps

1. **Read**: `TECHNICAL_IMPROVEMENTS_PHASE3.md` for detailed improvement docs
2. **Explore**: `templates/capabilities.py` to see registered templates
3. **Extend**: Create your own `CompositionAwareTemplate`
4. **Test**: Run unit tests on your template
5. **Register**: Add capabilities and test discovery
6. **Integrate**: Use in LLM planner via registry

Happy building! 🚀
