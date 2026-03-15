# Anima Studio - Quick Reference & Code Examples

## Quick Start: How to Use the System

### What You Need to Know

1. **3-Layer Architecture**: Prompt → LLM Plan (DSL) → Template Engine → Manim Code
2. **18 Templates**: 10 domain-specific + 8 primitives + 1 generic fallback
3. **3 Rendering Modes**: Single template, Composition (micro-templates), Generic DSL
4. **Scene Dependencies**: Order scenes via `depends_on` field
5. **Caching**: Plans cached in Redis for 24 hours

---

## Template Quick Reference

### When to Use Each Template Type

| Problem | Solution | Template | Example |
|---------|----------|----------|---------|
| Show matrix multiplication | Matrix class + numpy | `matrix_multiplication` | A×B=C |
| Explain linear transformation | Vector grid animation | `vector_transformation` | Grid morphing |
| Show eigenvectors | Vector preservation | `eigenvector` | Vector stays on line |
| Explain dot product | Projection visualization | `dot_product` | Vector projection |
| Animate derivative | Tangent line on curve | `derivative_tangent` | f'(x) at x=2 |
| Show integral | Shaded area under curve | `integral_area` | ∫₀² x² dx |
| Optimize function | Rolling ball down curve | `gradient_descent` | Local minimum |
| Show neural network | Nodes + connections | `neural_network` | 3-4-2 architecture |
| Explain attention | Token flow visualization | `transformer_attention` | 3 tokens → attention |
| Algorithm traversal | Node highlighting | `bfs_traversal` | BFS on graph |
| Custom combination | Mix micro-templates | Composition mode | Curve + points + arrows |
| Flexible animation | Declare objects + actions | `generic` | Anything not above |

---

## Code Examples

### Example 1: Simple Domain Template - Matrix Multiplication

**What's Needed**: Just the template name + parameters

```python
# In your request or directly:
plan_dict = {
    "title": "Matrix Multiplication",
    "template": "matrix_multiplication",
    "parameters": {
        "matrix_a": [[1, 2], [3, 4]],
        "matrix_b": [[2, 0], [1, 2]]
    }
}

# LLM generates this:
plan = AnimationPlan(**plan_dict)

# Template engine renders to:
# from manim import *
# class Scene1(Scene):
#     def construct(self):
#         matrix_a_val = [[1, 2], [3, 4]]
#         matrix_b_val = [[2, 0], [1, 2]]
#         m1 = Matrix(matrix_a_val).scale(0.8).to_edge(LEFT, buff=1)
#         m2 = Matrix(matrix_b_val).scale(0.8).next_to(m1, RIGHT, buff=0.5)
#         equals = MathTex('=')
#         res_val = np.dot(np.array(matrix_a_val), np.array(matrix_b_val)).tolist()
#         m3 = Matrix(res_val).scale(0.8).next_to(equals, RIGHT, buff=0.5)
#         group = VGroup(m1, m2, equals, m3).center()
#         
#         self.play(Write(m1), Write(m2))
#         self.wait(1)
#         self.play(Write(equals), Write(m3))
#         self.wait(2)
```

**Result**: Two matrices appear, equals sign appears, result matrix appears.

---

### Example 2: Composition Mode - Derivative Visualization

**What's Needed**: List of micro-templates to combine

```python
# LLM generates:
plan_dict = {
    "title": "Derivative as Tangent Line",
    "template": None,  # No single template
    "parameters": {
        "scenes": [
            {
                "scene_id": "intro",
                "description": "Draw parabola and point",
                "templates": ["draw_axis", "draw_curve", "place_point"],
                "parameters": {
                    "expression": "x**2",
                    "x": 1,
                    "color": "BLUE"
                },
                "narration": "Here's our parabola y=x² with a point at x=1"
            }
        ]
    }
}

plan = AnimationPlan(**plan_dict)

# Template engine renders:
# from manim import *
# config.background_color = '#0a0a0f'
# 
# class Scene1(Scene):
#     def construct(self):
#         # --- Scene: intro ---
#         # Narration: Here's our parabola y=x² with a point at x=1
#         
#         # draw_axis template:
#         ax = Axes(x_range=[-5, 5], y_range=[-3, 3], axis_config={'include_tip': True})
#         self.play(Create(ax))
#         
#         # draw_curve template:
#         curve = ax.plot(lambda x: x**2, color=BLUE)
#         self.play(Create(curve))
#         
#         # place_point template:
#         point = Dot(ax.c2p(1, 1**2), color=YELLOW)
#         self.play(FadeIn(point))
#         
#         self.next_section()
#         self.wait(1)
```

**Result**: Axes appear → parabola appears → point appears

---

### Example 3: Generic DSL Mode - Custom Animation

**What's Needed**: Explicit objects and animations

```python
# LLM generates:
plan_dict = {
    "title": "Bouncing Circles",
    "template": "generic",
    "parameters": {
        "scenes": [
            {
                "scene_id": "bounce",
                "description": "Three circles bounce across screen",
                "objects": [
                    {
                        "id": "circle1",
                        "type": "circle",
                        "parameters": {
                            "radius": 0.5,
                            "color": "BLUE",
                            "position": [-3, 0, 0]
                        }
                    },
                    {
                        "id": "circle2",
                        "type": "circle",
                        "parameters": {
                            "radius": 0.5,
                            "color": "RED",
                            "position": [0, 0, 0]
                        }
                    },
                    {
                        "id": "circle3",
                        "type": "circle",
                        "parameters": {
                            "radius": 0.5,
                            "color": "GREEN",
                            "position": [3, 0, 0]
                        }
                    },
                    {
                        "id": "label",
                        "type": "text",
                        "parameters": {
                            "text": "Bouncing Circles",
                            "position": [0, 3, 0]
                        }
                    }
                ],
                "animations": [
                    {"object_id": "circle1", "action": "fade_in"},
                    {"object_id": "circle2", "action": "fade_in"},
                    {"object_id": "circle3", "action": "fade_in"},
                    {"object_id": "label", "action": "write"},
                    {"object_id": "circle1", "action": "move", "parameters": {"to": [0, 2, 0]}},
                    {"object_id": "circle2", "action": "move", "parameters": {"to": [0, 2, 0]}},
                    {"object_id": "circle3", "action": "move", "parameters": {"to": [0, 2, 0]}},
                    {"object_id": "circle1", "action": "scale", "parameters": {"factor": 0.5}},
                    {"object_id": "circle2", "action": "scale", "parameters": {"factor": 0.5}},
                    {"object_id": "circle3", "action": "scale", "parameters": {"factor": 0.5}}
                ]
            }
        ]
    }
}

plan = AnimationPlan(**plan_dict)

# GenericAnimationTemplate interprets and renders:
# from manim import *
# config.background_color = '#0a0a0f'
# 
# class Scene1(Scene):
#     def construct(self):
#         # Generic Primitive Animation Sequence
#         # Scene: bounce
#         
#         # Create objects
#         circle1 = Circle(radius=0.5, color=BLUE)
#         circle1.move_to([-3, 0, 0])
#         circle2 = Circle(radius=0.5, color=RED)
#         circle2.move_to([0, 0, 0])
#         circle3 = Circle(radius=0.5, color=GREEN)
#         circle3.move_to([3, 0, 0])
#         label = Text('Bouncing Circles', font_size=32)
#         label.move_to([0, 3, 0])
#         
#         # Run animations
#         self.play(FadeIn(circle1))
#         self.play(FadeIn(circle2))
#         self.play(FadeIn(circle3))
#         self.play(Write(label))
#         self.play(circle1.animate.move_to([0, 2, 0]))
#         self.play(circle2.animate.move_to([0, 2, 0]))
#         self.play(circle3.animate.move_to([0, 2, 0]))
#         self.play(circle1.animate.scale(0.5))
#         self.play(circle2.animate.scale(0.5))
#         self.play(circle3.animate.scale(0.5))
#         self.wait(1)
```

**Result**: 3 circles + text appear → move up → shrink

---

### Example 4: Multi-Scene with Dependencies

**What's Needed**: Multiple scenes with `depends_on` ordering

```python
# LLM generates:
plan_dict = {
    "title": "Building a Neural Network",
    "template": None,
    "parameters": {
        "scenes": [
            {
                "scene_id": "step0",
                "description": "Introduce goal",
                "template": "generic",
                "objects": [
                    {"id": "title", "type": "text", "parameters": {"text": "Building a Neural Network"}}
                ],
                "animations": [
                    {"object_id": "title", "action": "write"}
                ],
                "depends_on": [],
                "narration": "Let's build a simple neural network"
            },
            {
                "scene_id": "step1",
                "description": "Input layer",
                "template": "neutral_network",
                "parameters": {"layers": [3, 4, 2]},
                "depends_on": ["step0"],
                "narration": "We start with an input layer..."
            },
            {
                "scene_id": "step2",
                "description": "Forward pass",
                "template": "generic",
                "objects": [
                    {"id": "arrow", "type": "arrow", "parameters": {"start": [-2, 0, 0], "end": [2, 0, 0]}}
                ],
                "animations": [
                    {"object_id": "arrow", "action": "fade_in"}
                ],
                "depends_on": ["step1"],
                "narration": "Now data flows forward..."
            }
        ]
    }
}

plan = AnimationPlan(**plan_dict)

# Execution order after topological sort:
# 1. step0 (no dependencies)
# 2. step1 (depends_on: ["step0"])
# 3. step2 (depends_on: ["step1"])

# Generated code:
# class Scene1(Scene):
#     def construct(self):
#         # Step 0: Introduction
#         title = Text('Building a Neural Network', font_size=32)
#         self.play(Write(title))
#         
#         self.next_section()
#         self.wait(1)
#         
#         # Step 1: Neutral network layers
#         [neural network code...]
#         
#         self.next_section()
#         self.wait(1)
#         
#         # Step 2: Forward pass
#         arrow = Arrow([-2, 0, 0], [2, 0, 0], color=GOLD)
#         self.play(FadeIn(arrow))
#         
#         self.next_section()
#         self.wait(1)
```

---

## Scene Object Types & Animation Actions Reference

### Object Types

```
SHAPE OBJECTS:
  circle      → Circle(radius=r, color=c)
  square      → Square(color=c)
  triangle    → Triangle(color=c)
  star        → Star(color=c)
  polygon     → RegularPolygon(n=sides, color=c)

POINT/LINE OBJECTS:
  dot         → Dot(color=c)
  line        → Line(start, end)
  arrow       → Arrow(start, end, color=c)
  vector      → Vector(coords, color=c)

TEXT/LABEL OBJECTS:
  text        → Text(text, font_size=32)

COMPOSITES (generic template):
  All above + curve, path, group
```

### Animation Actions

```
APPEARANCE:
  fade_in     → self.play(FadeIn(obj))          [no params]
  fade_out    → self.play(FadeOut(obj))         [no params]
  write       → self.play(Write(obj))           [no params]
  grow        → self.play(GrowFromCenter(obj))  [no params]
  
MOVEMENT:
  move        → obj.animate.move_to(pos)        [to: [x,y,z]]
  follow_path → MoveAlongPath(obj, path)        [path: "circle"|"line"]
  
TRANSFORMATION:
  scale       → obj.animate.scale(factor)       [factor: float]
  rotate      → Rotate(obj, angle)              [angle: degrees]
  color       → obj.animate.set_color(color)    [color: "YELLOW"]
  transform   → ReplacementTransform(obj, tgt)  [target: "obj_id"]
  
HIGHLIGHT:
  pulse       → self.play(Indicate(obj))        [no params]
  highlight   → self.play(Indicate(obj))        [no params]
```

---

## Template Selection Decision Tree

```
Does the prompt mention...?

┌─ matrix/multiply/determinant/inverse
│  └─→ matrix_multiplication
│
├─ vector/transformation/linear map
│  └─→ vector_transformation
│
├─ eigenvector/eigenvalue/preserved
│  └─→ eigenvector
│
├─ dot product/projection/scalar
│  └─→ dot_product
│
├─ derivative/tangent/rate of change
│  └─→ derivative_tangent
│
├─ integral/area/accumulation
│  └─→ integral_area
│
├─ gradient descent/optimization/minimize
│  └─→ gradient_descent
│
├─ neural/network/layer/node
│  └─→ neural_network
│
├─ transformer/attention/token
│  └─→ transformer_attention
│
├─ BFS/breadth-first/graph traversal
│  └─→ bfs_traversal
│
├─ curve + point on curve (simple)
│  └─→ compose: [draw_curve, place_point]
│
├─ axis + curve (simple)
│  └─→ compose: [draw_axis, draw_curve]
│
├─ arrow + text + shapes (custom)
│  └─→ generic DSL mode
│
└─ Complex/unclear
   └─→ generic DSL mode (most flexible)
```

---

## LLM Planning Process Flow

### Simple Case: Cache Hit

```
User: "Show matrix multiplication [1,2;3,4] * [5,6;7,8]"
    ↓
[Cache lookup: plan_v2:{md5hash}]
    ↓
HIT! Return cached AnimationPlan
    ↓
Skip all LLM processing
    ↓
Go straight to Template Engine
```

### Full Case: Cache Miss

```
User: "Explain how derivative is the tangent line slope"
    ↓
[Cache lookup: MISS]
    ↓
[Rule-based router: detect "derivative" → hint]
    ↓
[Gemini LLM call with full prompt]
    ↓
[Receive JSON with intent + plan]
    ↓
[Validate plan against intent]
    ↓
[If violations: repair loop]
    ↓
[Store in Redis cache]
    ↓
[Return AnimationPlan to Template Engine]
```

---

## Schema Comparison Table

| Component | Location | Purpose | Fields |
|-----------|----------|---------|--------|
| **AnimationPlan** | `schemas/animation.py` | Root DSL structure | title, template, parameters, scenes |
| **AnimationScene** | `schemas/animation.py` | Single scene spec | scene_id, template(s), depends_on, objects, animations, narration |
| **AnimationObject** | `schemas/animation.py` | Primitive object | id, type, parameters |
| **AnimationStep** | `schemas/animation.py` | Single animation | object_id, action, parameters |
| **UserIntent** | `schemas/intent.py` | Concept detection | concept, template, parameters, notes |
| **Job** | `models/job.py` | Database job record | id, prompt, status, plan_json, video_filename, code, error |
| **JobResponse** | `schemas/job.py` | API response | Same as Job + timestamps |

---

## Performance & Caching

### Cache Key Generation
```python
cache_key = f"plan_v2:{hashlib.md5(user_prompt.encode()).hexdigest()}"
# Example: "plan_v2:5d41402abc4b2a76b9719d911017c592"
```

### Cache Hit Details
- **Lookup Time**: ~1ms (Redis)
- **Return**: Full AnimationPlan object
- **Skip**: All LLM processing, validation, repair
- **Result**: Template engine gets plan instantly

### Cache Miss Details
- **Router**: ~1ms (regex patterns)
- **LLM Call**: ~5-15s (Gemini API)
- **Validation**: ~1ms (schema checks)
- **Repair** (if needed): ~5-15s (2nd LLM call)
- **Store**: ~1ms (Redis)
- **Total**: 7-31s first time, <1s afterward

### Caching Duration
- **TTL**: 24 hours
- **Eviction**: Automatic after 24h
- **Storage**: Serialized JSON in Redis
- **Purpose**: Avoid redundant LLM calls for same prompt

---

## Error Handling Flow

```
Error Type                  Location           Recovery
────────────────────────────────────────────────────────
GEMINI_API_KEY not set      generate_plan      Use fallback plan
Redis unavailable           generate_plan      Skip caching, continue
LLM call timeout            call_combined_llm  Retry loop (max 3)
Invalid JSON from LLM       _extract_json      Log error, try repair
Plan validation fails       validate_plan      Repair loop (2nd LLM)
Repair loop fails          repair_plan         Use original plan
Docker render timeout       render_graph_async Retry loop (max 3)
Scene1 class missing       render_graph_async Error to user
Manim syntax error         render_graph_async Error to user
```

---

## Common Prompt Patterns & Response

### Pattern 1: Domain Concept
```
Prompt: "Show matrix multiplication A=[1,2;3,4] B=[2,0;1,2]"
Router detects: "matrix" + "multiply"
→ Template: matrix_multiplication
→ Parameters: {matrix_a: [[1,2],[3,4]], matrix_b: [[2,0],[1,2]]}
→ LLM verification: Yes, this is matrix multiplication
```

### Pattern 2: Calculus Concept
```
Prompt: "Explain the derivative using a tangent line"
Router detects: "derivative" or "tangent"
→ Template: derivative_tangent
→ Parameters: {expression: "x**2"} (default)
→ LLM can override or use defaults
```

### Pattern 3: Multi-Step Explanation
```
Prompt: "First show a parabola, then show the tangent line at x=1"
Router: No clear single match
→ Template: null (composition)
→ Scenes: [scene_intro, scene_tangent]
→ Templates: scene_intro uses draw_curve
→ Templates: scene_tangent uses place_point, draw_arrow
```

### Pattern 4: Custom/Unusual Request
```
Prompt: "Animate 5 spinning triangles that transform into a circle"
Router: No match
→ Template: generic
→ Objects: [triangle1, triangle2, triangle3, triangle4, triangle5]
→ Animations: [spin triangle1, spin triangle2, ..., transform to circle]
```

---

## Testing & Validation Checklist

### Plan Validation Checks

```python
def validate_plan_against_intent(plan, intent, prompt) -> list[str]:
    violations = []
    
    # ✓ Check 1: Template exists
    if plan.template and plan.template not in AVAILABLE_TEMPLATES:
        violations.append(f"Unknown template: {plan.template}")
    
    # ✓ Check 2: Scene count reasonable
    if plan.template == "generic":
        scenes = plan.parameters.get("scenes", [])
        if not scenes:
            violations.append("Generic template must have 'scenes'")
        if len(scenes) > 6:
            violations.append(f"Too many scenes: {len(scenes)} > 6")
    
    # ✓ Check 3: Dependency validity (implicit)
    # ✗ NO cycle detection (limitation)
    # ✗ NO object_id validation (limitation)
    # ✗ NO action validation (limitation)
    
    return violations
```

---

## Integration Points

### With LLM Service
```python
# llm.py provides:
- generate_plan(prompt) → AnimationPlan
- generate_manim_code(prompt) → str (direct Gemini call)

# Called from:
- render_graph_async in tasks.py
- API routes (if any)
```

### With Database
```python
# Job model stores:
- plan_json: Dict → Serialized AnimationPlan.model_dump()
- code: str → Generated Manim code
- status: JobStatus (PENDING, RUNNING, SUCCEEDED, FAILED)

# Updated in:
- render_graph_async() during rendering
```

### With Docker
```python
# Container: anima_manim_renderer
# Mount point: /manim/
# Input: /manim/scene.py (Python script)
# Output: /manim/outputs/{job_id}.mp4
# Command: manim -qh scene.py Scene1 -o output.mp4
```

---

## Key Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `base.py` | ~30 | BaseTemplate abstract class |
| `engine.py` | ~120 | Template registry + render functions |
| `generic.py` | ~80 | GenericAnimationTemplate (DSL interpreter) |
| `primitives.py` | ~80 | 8 micro-templates |
| `linear_algebra/templates.py` | ~80 | 4 math templates |
| `calculus/templates.py` | ~70 | 3 calculus templates |
| `machine_learning/templates.py` | ~70 | 2 ML templates |
| `algorithms/templates.py` | ~30 | 1 algorithm template |
| `schemas/animation.py` | ~70 | AnimationPlan, Scene, Object, Step schemas |
| `schemas/intent.py` | ~15 | UserIntent schema |
| `llm.py` | ~300 | Gemini planner, caching, validation |
| `tasks.py` | ~450 | render_graph_async, Docker integration |

**Total**: ~1,400 lines of template + schema + LLM code

