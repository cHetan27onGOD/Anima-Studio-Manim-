# Anima Studio - Executive Summary: Template System Overview

## System at a Glance

The Anima Studio animation system uses a **3-tier architecture** to convert natural language prompts into professional mathematics animations:

```
User Prompt → LLM Planner (DSL) → Template Engine → Manim Code → Docker Render → MP4 Video
```

---

## Key Findings

### 1. **Current Template Structure** ✅

**18 Total Templates Organized by Category:**

| Category | Count | Examples | Use Case |
|----------|-------|----------|----------|
| **Domain-Specific** | 10 | Matrix, Derivative, Neural Network | Specialized math/CS concepts |
| **Micro-Primitives** | 8 | DrawCurve, PlacePoint, WriteText | Reusable building blocks |
| **Generic Fallback** | 1 | GenericAnimationTemplate | Any custom animation |

**File Organization:**
```
templates/
├── base.py                      # BaseTemplate (abstract parent)
├── engine.py                    # Registry + render_multi_scene_plan()
├── generic.py                   # DSL interpreter
├── primitives.py                # 8 micro-templates
├── linear_algebra/templates.py  # 4 templates
├── calculus/templates.py        # 3 templates
├── machine_learning/templates.py # 2 templates
└── algorithms/templates.py      # 1 template
```

**Key Design**: All inherit from `BaseTemplate`, implement `generate_construct_code()` returning Manim Python code for animations.

---

### 2. **AnimationPlan Schema** ✅

The DSL is a Pydantic model hierarchy:

```python
AnimationPlan
├── title: str                    # "Matrix Multiplication"
├── template: Optional[str]       # "matrix_multiplication" or null
├── parameters: Dict
│   └── scenes: List[AnimationScene]
│
AnimationScene
├── scene_id: str                 # "intro", "mechanism"
├── depends_on: List[str]         # ["intro"] → dependency ordering
├── template: str | templates: List[str]  # Single vs. composition mode
├── objects: List[AnimationObject]
├── animations: List[AnimationStep]
├── narration: str
├── parameters: Dict              # Template-specific params
│
AnimationObject
├── id: str
├── type: str                     # "circle", "text", "arrow", etc.
├── parameters: Dict              # {radius, color, position}
│
AnimationStep
├── object_id: str
├── action: str                   # "fade_in", "move", "transform"
├── parameters: Dict              # {to, factor, angle, target}
```

**Supporting Schema:**
- `UserIntent`: Concept detection (matrix, derivative, neural, etc.)
- `Job`: Database record with plan_json storage

---

### 3. **LLM Planner Logic** ✅

**6-Step Pipeline in `generate_plan()`:**

```
1. Check Redis Cache (key: plan_v2:{md5(prompt)})
   ↓
2. Rule-Based Router (detect domain hints)
   ↓
3. Gemini LLM Call (single combined prompt)
   - Injects 18 template names
   - Explains DSL primitives (objects, actions)
   - Provides required JSON format
   - Uses low temperature (0.2)
   ↓
4. Validate Plan
   - Check template in registry ✓
   - Check scene count ≤ 6 ✓
   - Check generic has scenes ✓
   ↓
5. Repair Loop (if violations)
   - Second LLM call to fix issues
   ↓
6. Store in Cache (24h TTL)
```

**Key Features:**
- Single LLM call generates both intent + plan
- Validation + repair loop ensures schema compliance
- Redis caching (24h) prevents redundant API calls
- Fallback to "Hello World" plan if LLM fails

---

### 4. **Scene Organization & Execution** ✅

**Three Rendering Modes:**

#### Mode 1: Single Template (Domain-Specific)
```python
{
  "template": "matrix_multiplication",
  "parameters": {"matrix_a": [...], "matrix_b": [...]}
}
# → MatrixMultiplicationTemplate instantiated + executed
```

#### Mode 2: Composition (Micro-Templates)
```python
{
  "templates": ["draw_axis", "draw_curve", "place_point"],
  "parameters": {"expression": "x**2", "x": 1}
}
# → Each template renders sequentially, outputs concatenated
```

#### Mode 3: Generic DSL (Declarative)
```python
{
  "objects": [
    {"id": "circle1", "type": "circle", "parameters": {...}},
    ...
  ],
  "animations": [
    {"object_id": "circle1", "action": "fade_in"},
    {"object_id": "circle1", "action": "move", "parameters": {"to": [2, 0, 0]}}
  ]
}
# → GenericAnimationTemplate interprets objects/actions
```

**Scene Dependencies:**
```python
depends_on: ["scene1", "scene2"]  # Ensures ordering via topological sort
# Output: All scenes execute in correct order within single Scene1 class
```

**Multi-Scene Output Structure:**
```python
class Scene1(Scene):
    def construct(self):
        # Scene 1 code
        self.next_section()
        self.wait(1)
        
        # Scene 2 code
        self.next_section()
        self.wait(1)
        
        # Scene 3 code
```

---

## Template Capabilities Matrix

### Supported Object Types (Generic Template)
```
Shapes:     circle, square, triangle, star, polygon, dot
Lines:      line, arrow, vector
Text:       text (with font_size)
Advanced:   curve, path (for follow_path), group
```

### Supported Animation Actions (Generic Template)
```
Appearance: fade_in, fade_out, write, grow
Movement:   move (to position), follow_path
Transform:  scale (by factor), rotate (by angle), color change
Compound:   transform (object → object), pulse/highlight
```

### Domain-Specific Capabilities
| Template | Capability |
|----------|-----------|
| MatrixMultiplication | 2D matrix display + numpy multiplication |
| VectorTransformation | Grid morphing, transformation visualization |
| DerivativeTangent | Curve with sliding tangent + ValueTracker |
| IntegralArea | Curve with shaded region under it |
| GradientDescent | Ball rolling down parabola, point following |
| NeuralNetwork | Nodes arranged in layers, connected by lines |
| TransformerAttention | Token boxes + attention flow arrows |
| BFSTraversal | Node highlighting in traversal order |

---

## Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION PIPELINE                           │
└─────────────────────────────────────────────────────────────────┘

User Prompt
    ↓
[render_graph_async in tasks.py]
    ├─ Step 1: generate_plan(prompt)
    │   ├─ Check Redis cache
    │   ├─ Rule-based router
    │   ├─ Gemini LLM call
    │   ├─ Validate + Repair
    │   └─ Return: AnimationPlan
    │
    ├─ Step 2: render_multi_scene_plan(plan)
    │   ├─ Sort scenes by dependencies
    │   ├─ For each scene:
    │   │   ├─ Check templates list (composition) OR template field (single)
    │   │   ├─ Render each template's generate_construct_code()
    │   │   └─ Add section breaks
    │   └─ Return: Full Python code string
    │
    ├─ Step 3: Docker Render
    │   ├─ Copy script to /manim/scene.py
    │   ├─ Execute: manim -qh scene.py Scene1 -o output.mp4
    │   └─ Copy to /manim/outputs/
    │
    └─ Step 4: Store Results
        └─ Update DB: video_filename, code, status=SUCCEEDED

Result: MP4 Video File
```

---

## Caching Strategy

| Layer | Technology | Duration | Impact |
|-------|-----------|----------|---------|
| **Plans** | Redis | 24 hours | Avoids LLM calls for repeated prompts |
| **Code** | Database | Permanent | Debug + re-render capability |
| **Videos** | File system | Permanent | Gallery/history |

**Cache Key**: `plan_v2:{md5(user_prompt)}`

---

## Strengths of Current System

✅ **Modular Design**: 18 reusable templates covering major math/CS domains
✅ **Flexible Rendering**: 3 modes (single, composition, generic DSL) cover diverse needs
✅ **Smart Planning**: LLM with validation + repair ensures valid plans
✅ **Efficient Caching**: Redis prevents redundant LLM calls
✅ **Fallback Safety**: Always produces valid output (worst: "Hello World")
✅ **Dependency Handling**: Scene ordering via `depends_on` field
✅ **Docker Isolation**: Safe rendering in containerized environment
✅ **Full Code Storage**: Generated code available for inspection/debugging

---

## Current Limitations

⚠️ **Composition State**: Micro-templates don't share state between renders (each independent)
⚠️ **Cycle Detection**: No check for circular dependencies in scenes
⚠️ **Validation Depth**: Only checks for template existence and scene count
⚠️ **Error Messages**: Limited feedback from validation to LLM for intelligent repair
⚠️ **Template Parameters**: No schema validation for template-specific parameters
⚠️ **LLM Fallibility**: If Gemini produces malformed JSON, repair may fail
⚠️ **Single Scene Class**: All animation output is one Manim Scene1 (no multi-class support)
⚠️ **No Hot Reload**: Template changes require server restart

---

## Complete File Reference

### Template Engine Files (330 lines)
- **base.py** (30L): `BaseTemplate` ABC
- **engine.py** (120L): `TEMPLATES` registry, `render_template()`, `render_multi_scene_plan()`
- **generic.py** (80L): `GenericAnimationTemplate` DSL interpreter
- **primitives.py** (100L): 8 micro-templates

### Domain Template Files (360 lines)
- **linear_algebra/templates.py** (80L): MatrixMultiplication, VectorTransformation, Eigenvector, DotProduct
- **calculus/templates.py** (70L): DerivativeTangent, IntegralArea, GradientDescent
- **machine_learning/templates.py** (70L): NeuralNetwork, TransformerAttention
- **algorithms/templates.py** (30L): BFSTraversal

### Schema Definition Files (100 lines)
- **schemas/animation.py** (70L): AnimationPlan, Scene, Object, Step
- **schemas/intent.py** (15L): UserIntent
- **schemas/job.py** (20L): JobResponse

### Planning & Execution Files (750 lines)
- **services/llm.py** (350L): Gemini integration, caching, validation, repair
- **worker/tasks.py** (450L): render_graph_async, Docker integration, job lifecycle

---

## Quick Start Guide for Developers

### To Add a New Domain Template:
1. Create class in new folder: `templates/{domain}/templates.py`
2. Inherit from `BaseTemplate`
3. Implement `generate_construct_code()` returning indented Manim code
4. Register in `TEMPLATES` dict in `engine.py`
5. Update LLM prompt to document the new template

### To Understand Execution:
1. Read `tasks.py` → `render_graph_async()` for full flow
2. Read `llm.py` → `generate_plan()` for LLM planning
3. Read `engine.py` → `render_multi_scene_plan()` for template rendering

### To Debug a Failed Animation:
1. Check `Job.logs` for error messages
2. Check `Job.code` for generated Manim script
3. Check `Job.error` for exception details
4. Look at `plan_json` to inspect DSL structure

---

## Conclusion

The Anima Studio template system is a sophisticated **3-tier architecture** that:

1. **Plans**: Uses Gemini LLM to convert natural language → structured DSL with caching
2. **Renders**: Uses 18 specialized template classes to convert DSL → professional Manim code
3. **Executes**: Uses Docker to safely render Manim code → MP4 videos

The design emphasizes **modularity** (reusable templates), **flexibility** (3 rendering modes), and **reliability** (validation + fallbacks). The current implementation successfully handles standard mathematical animations and provides a clear extension point for new domains.

---

## Supporting Documentation

See also:
- **TEMPLATE_SYSTEM_OVERVIEW.md** - Comprehensive detailed reference with code examples
- **QUICK_REFERENCE.md** - Code examples, quick decision trees, checklists
- **Visual Architecture Diagrams** - See flowcharts for complete system flow, schema relationships, LLM pipeline
