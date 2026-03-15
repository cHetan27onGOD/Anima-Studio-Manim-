# Technical Improvements & Phase 3 Architecture

## Overview

This document describes three critical architectural improvements implemented after Phase 2, plus the scaffolding for Phase 3 engines.

---

## Improvement 1: Object Namespace Isolation

**Problem**: Objects in CompositionContext are global, causing collisions when multiple scenes create objects with the same name.

**Solution**: Automatic scene-level namespacing.

### How It Works

```
Scene 1 creates: "vector"
 ↓
Internally stored as: "scene1_vector"
 ↓
Templates refer to logical name: "vector"
 ↓
CompositionContext handles mapping
```

### Implementation

**File**: `templates/composition.py`

```python
class CompositionContext:
    def _namespace(self, logical_id: str) -> str:
        """Convert logical ID to internal namespaced ID"""
        return f"{self.scene_id}_{logical_id}"
    
    def add_object(self, logical_id: str, ...):
        namespaced_id = self._namespace(logical_id)
        # Store with namespaced ID
```

### Benefits

✅ **No Name Collisions**: Different scenes can use same object names
✅ **Clean API**: Templates use logical IDs (e.g., "vector")
✅ **Transparent**: Namespacing is automatic and invisible to templates
✅ **Future-Ready**: Enables cross-scene object references if needed

### Example

```python
# Scene 1: Draw curve and point
composer1 = TemplateComposer("scene1")
composer1.add_template(DrawCurveTemplate(...))  # creates "curve"
composer1.add_template(PlacePointTemplate(...)) # creates "point"

# Scene 2: Another curve and point (NO COLLISION)
composer2 = TemplateComposer("scene2")
composer2.add_template(DrawCurveTemplate(...))  # creates "curve" (different from scene1)
composer2.add_template(PlacePointTemplate(...)) # creates "point" (different from scene1)

# Internally:
# scene1_curve, scene1_point
# scene2_curve, scene2_point
```

---

## Improvement 2: Scene Duration Estimation

**Problem**: Scene durations are static or manually specified, making it hard to:
- Sync narration with animation
- Estimate total video length
- Optimize rendering

**Solution**: Automatic duration estimation from animation steps.

### How It Works

**File**: `schemas/animation.py`

Each `AnimationStep` has a duration heuristic:

```python
DURATION_MAP = {
    "fade_in": 0.5,
    "write": 2.0,
    "draw": 2.0,
    "transform": 2.0,
    "move": 1.5,
    "highlight": 1.0,
    ...
}
```

**AnimationScene calculates total:**

```python
scene.calculate_estimated_duration() 
    = sum(step.estimate_duration() for step in animations) + 1.0 (buffer)
```

### Advanced: Narration Duration Sync

**File**: `services/narration.py` → `NarrationDurationCalculator`

```python
narration_duration = estimate_duration(
    "Explain eigenvectors...",
    rate="normal"  # 140 WPM
) 
# Returns: 4.2 seconds

scene.duration = max(
    animation_duration,  # 3.0s
    narration_duration   # 4.2s
)
# Result: 4.2s (ensures narration completes)
```

### Benefits

✅ **Automatic Timing**: No manual duration entry needed
✅ **Accurate Narration Sync**: Voice-over won't be cut off
✅ **Total Duration Prediction**: Plan generation cost before rendering
✅ **Optimization Ready**: Duration data enables parallelization

### Example

```python
plan = AnimationPlan(...)

# Get total duration (all scenes + buffer)
total_seconds = plan.calculate_total_duration()

# Get metadata with breakdown
metadata = plan.get_metadata()
# {
#     "total_duration": 45.3,
#     "average_scene_duration": 7.5,
#     "narration_lines": 6,
#     "execution_order": ["intro", "mechanism", "result"]
# }
```

---

## Improvement 3: Template Capability Metadata

**Problem**: LLM planner decides templates from keywords, which leads to hallucinated/incorrect templates.

**Solution**: Each template declares capabilities (concepts it covers, composition readiness, etc).

### How It Works

**File**: `templates/capabilities.py`

```python
class TemplateCapabilities:
    template_id: str
    concepts: Set[str]  # ["eigenvectors", "linear_transformation"]
    composition_ready: bool  # Can be used in multi-template scenes
    estimated_duration: float  # Typical scene length
```

**Global Registry**:

```python
registry = CapabilityRegistry()

register_template_capabilities(
    "eigenvectors_advanced",
    concepts={"eigenvectors", "eigenvalues", "stable direction"},
    composition_ready=True,
    duration=8.0
)
```

### Smart Routing

Instead of keyword matching:

```python
# OLD: Brittle keyword matching
if "eigenvector" in prompt:
    template = "eigenvectors_advanced"  # Hope it exists!

# NEW: Capability-based matching
templates = registry.find_templates_for_concept("eigenvectors")
# Returns: ["eigenvectors_advanced", "eigen_decomposition", ...]
# Ranked by match score
```

### Benefits

✅ **No Hallucination**: Only registered templates returned
✅ **Fuzzy Matching**: Handles variations (eigenvalue vs eigenvector)
✅ **Ranking**: Best matches first
✅ **Self-Describing**: Templates document themselves
✅ **Extensible**: Easy to add new templates

### Usage in LLM Planner

**File**: `services/llm.py`

```python
# Instead of rule_based_concept_router using keywords,
# use capabilities registry:

registry = get_capability_registry()
templates = registry.find_templates_for_concept(
    "eigenvectors",
    composition_mode=True
)
# Returns: ["eigenvectors_advanced", "draw_axis", "create_vector"]

# Pass to LLM as context:
prompt += f"Available templates: {templates}"
```

---

## Phase 3 Scaffolding: Narration Engine

The three improvements above enable the Phase 3 narration system.

**File**: `services/narration.py`

### Engine 1: Narration Generator

```python
generator = NarrationGenerator()

narration = generator.generate_narration_for_scene(
    scene=AnimationScene(...),
    concept="eigenvectors"
)
# Returns: "Notice how this vector stays on its line..."
```

**Strategies**:
1. Use existing scene narration (manual)
2. Infer from template capabilities
3. Generate with LLM (future enhancement)
4. Use pattern templates for common structures

### Engine 2: Duration Sync

```python
calculator = NarrationDurationCalculator()

duration = calculator.sync_scene_duration(
    scene,
    rate="normal"  # 140 WPM
)
# Ensures animation + narration fit in duration
```

**Speaking rates**:
- Slow: 100 WPM (for dense concepts)
- Normal: 140 WPM
- Fast: 180 WPM

### Engine 3: Concept Expansion

```python
expander = ConceptExpander()

templates = expander.expand_concept(
    "eigenvectors",
    max_scenes=5
)
# Returns: ["draw_axis", "create_vector", "eigenvectors_advanced", ...]
# In pedagogical order
```

**Builds scaffold of scenes automatically:**
- Prerequisites (vector space)
- Main concept (eigenvectors)
- Deepening (eigenvalues, stability)

### Complete Pipeline

```python
pipeline = NarrationPipeline()

annotated_plan = pipeline.process_plan(plan)
# ↓
# Step 1: Generate missing narration
# Step 2: Sync scene durations
# Step 3: Calculate total duration
# ↓
# Returns: Plan ready for rendering + voice synthesis
```

---

## Integration Points

### How Improvements Work Together

```
User Prompt
  ↓
[Concept Router - Uses CapabilityRegistry]
  ↓ discovers: eigenvectors
  ↓
[LLM Planner - Uses Capabilities for smart routing]
  ↓ selects: eigenvectors_advanced, composition templates
  ↓
[AnimationPlan - Uses Duration Estimation]
  ↓ calculates: total time 45.3s
  ↓
[NarrationPipeline - Uses all three improvements]
  ↓
  ├─ Gets capability metadata
  ├─ Generates narration from concepts
  ├─ Syncs durations to narration
  ├─ Namespaces objects automatically
  ↓
[Final Plan - Ready for rendering]
  ├─ All scenes have narration
  ├─ Durations are accurate
  ├─ No naming conflicts
  └─ Metadata includes voice requirements
```

---

## Architecture Comparison

### Before Improvements

```
Template
  ↓
No metadata (LLM guesses capabilities)
  ↓
Objects: Global scope (collisions)
  ↓
Durations: Manual or generic (inaccurate)
  ↓
Narration: User-provided or missing
  ↓
Result: Incomplete, error-prone
```

### After Improvements

```
Template
  ↓
TemplateCapabilities (self-describing)
  ↓
Objects: Scene-namespaced (safe)
  ↓
Durations: Auto-estimated (accurate)
  ↓
Narration: Generated + synced (complete)
  ↓
Result: Complete, robust, auto-optimized
```

---

## Code Examples

### Example 1: Namespace Isolation

```python
# Two scenes creating "vector"
scene1 = AnimationScene(scene_id="vector_space")
scene2 = AnimationScene(scene_id="transformation")

ctx1 = CompositionContext("vector_space")
ctx2 = CompositionContext("transformation")

# Scene 1
ctx1.add_object("vector", "vector", "vec1 = Vector([1,0])")
# Stored as: "vector_space_vector"

# Scene 2
ctx2.add_object("vector", "vector", "vec2 = Vector([2,1])")
# Stored as: "transformation_vector"

# No collision!
assert ctx1.objects["vector_space_vector"].object_id != \
       ctx2.objects["transformation_vector"].object_id
```

### Example 2: Duration Estimation

```python
scene = AnimationScene(
    scene_id="derivative",
    narration="Explain how the derivative represents slope. " * 10,
    animations=[
        AnimationStep(action="draw", duration=2.0),
        AnimationStep(action="highlight", duration=1.0),
    ]
)

# Auto-estimate
animation_duration = scene.calculate_estimated_duration()  # ~4s

# Narration duration
narration_duration = scene.estimate_narration_duration()   # ~6s

# Use max
scene.duration = max(animation_duration, narration_duration)  # 6s
```

### Example 3: Capability-Based Routing

```python
registry = CapabilityRegistry()

# Find templates for "eigenvectors"
templates = registry.find_templates_for_concept("eigenvectors")
# Returns: [
#   ("eigenvectors_advanced", 1.0),    # Perfect match
#   ("linear_transformation", 0.7),    # Related
#   ("transform_object", 0.5),         # Partial
# ]

# Only get composition-ready
composition = registry.find_templates_for_concept(
    "eigenvectors",
    composition_mode=True
)
# Returns: ["eigenvectors_advanced", "create_vector", ...]
```

---

## Testing Improvements

### Test Case 1: Namespace Isolation

```python
def test_namespace_isolation():
    ctx1 = CompositionContext("scene1")
    ctx2 = CompositionContext("scene2")
    
    ctx1.add_object("vector", "vector", "...")
    ctx2.add_object("vector", "vector", "...")
    
    # Should be different
    assert ctx1.get_object("vector") != ctx2.get_object("vector")
    
    # But templates refer to same logical name
    assert "vector" in ctx1.get_available_objects()
    assert "vector" in ctx2.get_available_objects()
```

### Test Case 2: Duration Sync

```python
def test_duration_sync():
    scene = AnimationScene(
        narration="This is a test. " * 30,  # ~10 words
        animations=[AnimationStep(action="draw")]
    )
    
    narration_s = scene.estimate_narration_duration()
    animation_s = scene.get_effective_duration()
    
    # Narration is longer
    assert narration_s > animation_s
    
    # When synced, uses max
    assert scene.get_effective_duration() >= narration_s
```

### Test Case 3: Capability Matching

```python
def test_capability_matching():
    registry = CapabilityRegistry()
    
    register_template_capabilities(
        "eigenvectors_advanced",
        concepts={"eigenvectors", "eigenvalues"}
    )
    
    # Exact match
    assert "eigenvectors_advanced" in \
        registry.find_templates_for_concept("eigenvectors")
    
    # Fuzzy match
    assert "eigenvectors_advanced" in \
        registry.find_templates_for_concept("eigen")
```

---

## Next Steps

### Immediate (Week 1)
- ✅ Namespace isolation complete
- ✅ Duration estimation complete
- ✅ Capability metadata scaffolded
- [ ] Test all three improvements
- [ ] Integrate with LLM planner
- [ ] Update documentation

### Phase 3 Full Implementation (Week 2-3)
- [ ] LLM-based narration generation
- [ ] Voice synthesis integration (ElevenLabs/Coqui)
- [ ] Scene graph optimizer
- [ ] Concept knowledge graph

### Phase 3.5 Advanced Features (Week 4+)
- [ ] Interactive scene editor
- [ ] Community template gallery
- [ ] Analytics dashboard
- [ ] Multi-language support

---

## Files Modified/Created

| File | Purpose | Type |
|------|---------|------|
| `templates/composition.py` | Namespace isolation | Modified |
| `templates/capabilities.py` | Capability registry | NEW |
| `schemas/animation.py` | Duration estimation | Modified |
| `services/narration.py` | Narration engine | NEW |

Total lines of code added: ~800
Integration complexity: Medium (mostly standalone modules)
