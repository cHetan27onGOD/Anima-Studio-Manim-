# 📚 Anima Studio Documentation Index

## 📋 Quick Navigation

### Start Here 👇
- **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - High-level overview (5 min read)
  - System architecture at a glance
  - Key findings on templates, schemas, LLM logic
  - Strengths and limitations
  - File references

### For Deep Understanding 🔍
- **[TEMPLATE_SYSTEM_OVERVIEW.md](TEMPLATE_SYSTEM_OVERVIEW.md)** - Comprehensive reference (15 min read)
  - Complete system overview with architecture flow diagram
  - Template structure (18 total templates)
  - Schema definitions (AnimationPlan, Scene, Object, Step)
  - Template engine deep dive (render functions)
  - LLM planner system (6-step pipeline)
  - Execution layer (render_graph_async)
  - Code examples for each rendering mode
  - Scene dependency system
  - Composition mode details
  - Fallback strategies
  - Caching implementation

### For Code Examples & Quick Lookup 🚀
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Practical guide (10 min read)
  - When to use each template
  - 4 complete code examples
  - Object types & animation actions
  - Template selection decision tree
  - LLM planning process flow
  - Schema comparison table
  - Performance & caching details
  - Error handling flow
  - Common prompt patterns
  - Testing checklist
  - Integration points

---

## 📊 System Architecture Overview

```
USER INPUT
    ↓
┌─────────────────────────────────────┐
│   LLM PLANNER (services/llm.py)     │
│   - Gemini API integration          │
│   - Redis caching (24h)             │
│   - Rule-based concept router       │
│   - Validation + repair loop        │
│   - Returns: AnimationPlan DSL      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  TEMPLATE ENGINE (templates/)        │
│  - 18 template classes              │
│  - render_multi_scene_plan()       │
│  - Dependency sorting               │
│  - Returns: Manim Python code       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  DOCKER RENDERER (worker/tasks.py)  │
│  - Copy script to container         │
│  - Execute Manim                    │
│  - Return MP4 video                 │
└─────────────────────────────────────┘
    ↓
MP4 VIDEO OUTPUT
```

---

## 📦 Component Breakdown

### Templates (18 Total)

#### Domain-Specific (10)
- **Linear Algebra (4)**
  - MatrixMultiplication - A×B=C with numpy
  - VectorTransformation - Grid morphing
  - Eigenvector - Vector preservation
  - DotProduct - Projection visualization

- **Calculus (3)**
  - DerivativeTangent - Tangent line on curve
  - IntegralArea - Shaded area under curve
  - GradientDescent - Ball rolling optimization

- **Machine Learning (2)**
  - NeuralNetwork - Nodes + connections
  - TransformerAttention - Token flow visualization

- **Algorithms (1)**
  - BFSTraversal - Graph traversal animation

#### Micro-Primitives (8)
- DrawCurve, PlacePoint, DrawArrow, HighlightObject
- DrawAxis, WriteText, CreateVector, TransformObject

#### Fallback (1)
- GenericAnimationTemplate - DSL interpreter

### Schemas (4 Main Pydantic Models)
- **AnimationPlan** - Root DSL structure
- **AnimationScene** - Per-scene specification with dependencies
- **AnimationObject** - Primitive objects (circle, text, etc.)
- **AnimationStep** - Animation actions (fade_in, move, etc.)

### Rendering Modes (3)
1. **Single Template** - Direct domain-specific template
2. **Composition** - Multiple micro-templates combined
3. **Generic DSL** - Declarative objects + animations

---

## 🔑 Key Concepts

### AnimationPlan DSL
```
{
  title: str
  template: Optional[str]
  parameters: {
    scenes: [AnimationScene]
  }
}
```

### AnimationScene Structure
```
{
  scene_id: str
  depends_on: [str]        # ← Dependency ordering
  template: str | null
  templates: [str]         # ← Composition mode
  objects: [AnimationObject]
  animations: [AnimationStep]
  narration: str
}
```

### LLM Planning Pipeline
```
Cache Check → Router → Gemini LLM → Validate → Repair (if needed) → Cache Store
```

### Template Execution
```
Instantiate → generate_construct_code() → Format output → (Concatenate if composition)
```

---

## 📁 File Organization

```
backend/app/
├── templates/
│   ├── base.py                         # BaseTemplate ABC
│   ├── engine.py                       # Registry + render functions ⭐
│   ├── generic.py                      # DSL interpreter
│   ├── primitives.py                   # 8 micro-templates
│   ├── linear_algebra/templates.py     # 4 templates
│   ├── calculus/templates.py           # 3 templates
│   ├── machine_learning/templates.py   # 2 templates
│   └── algorithms/templates.py         # 1 template
│
├── schemas/
│   ├── animation.py                    # AnimationPlan, Scene, Object, Step ⭐
│   └── intent.py                       # UserIntent
│
├── services/
│   └── llm.py                          # Gemini integration + planning ⭐
│
└── worker/
    └── tasks.py                        # render_graph_async ⭐
```

**⭐ = Essential files to understand**

---

## 🎯 For Different Roles

### For Product/Design
→ Read: EXECUTIVE_SUMMARY.md
- Understand capabilities and limitations
- See what's possible with 18 templates
- Understand 3 rendering modes

### For Backend Engineers
→ Read: TEMPLATE_SYSTEM_OVERVIEW.md + QUICK_REFERENCE.md
- Understand each template class
- Learn DSL schema structure
- See LLM planning pipeline
- Study render_multi_scene_plan()

### For ML/LLM Engineers
→ Read: QUICK_REFERENCE.md "LLM Planning Process"
- Understand prompt engineering approach
- See caching strategy
- Learn validation + repair loop
- Study error handling

### For QA/Testing
→ Read: QUICK_REFERENCE.md "Testing & Validation"
- See validation checks
- Understand error scenarios
- Learn fallback strategies

### For New Contributors
→ Read: QUICK_REFERENCE.md "To Add a New Template"
- See template implementation steps
- Understand pattern for new domains
- Learn where to register

---

## 🔄 Common Workflows

### Workflow 1: How a Prompt Becomes a Video
```
1. User submits prompt
2. LLM planner generates AnimationPlan (with caching)
3. Template engine converts to Manim code
4. Docker renders Manim → MP4
5. Return video to user
```

### Workflow 2: Cache Hit vs Miss
```
CACHE HIT (same prompt repeated):
Prompt → Redis lookup (1ms) → AnimationPlan → Template → Video
TOTAL: ~30-60s

CACHE MISS (new prompt):
Prompt → Router (1ms) → Gemini (5-15s) → Validate (1ms) → Store (1ms) → Template → Video
TOTAL: ~35-75s
```

### Workflow 3: Composition Mode (Multiple Templates)
```
Scene {
  templates: ["draw_axis", "draw_curve", "place_point"]
  parameters: {expression: "x**2", x: 1}
}
↓
render_multi_scene_plan() renders:
1. DrawAxisTemplate.generate_construct_code()
2. DrawCurveTemplate.generate_construct_code()
3. PlacePointTemplate.generate_construct_code()
↓
Concatenate all code into single Scene1.construct()
```

---

## 🐛 Troubleshooting

### Issue: LLM returns invalid JSON
→ Check llm.py → _extract_json()
→ Handles markdown code blocks
→ Falls back to attempting repair

### Issue: Plan validation fails
→ Check validate_plan_against_intent()
→ Checks: template exists, scene count, etc.
→ Triggers repair loop with 2nd LLM call

### Issue: Manim render fails
→ Check Job.logs for Manim error
→ Check Job.code for generated script
→ Verify Docker container running

### Issue: Composition mode doesn't work
→ Check order of templates in templates[] list
→ Verify each template works standalone
→ Check that parameters are shared across templates

---

## 📈 Performance Characteristics

| Operation | Duration | Notes |
|-----------|----------|-------|
| Cache hit | 1ms | Redis lookup |
| Router | 1ms | Regex pattern matching |
| Gemini LLM | 5-15s | API call timeout: 30s |
| Validate | 1ms | Schema checks |
| Repair | 5-15s | 2nd LLM call (if needed) |
| Store cache | 1ms | Redis setex |
| Template render | <1s | Generate Python code |
| Docker render | 30-60s | Manim animation generation |
| **Total (cache hit)** | 1-5s | From plan to code |
| **Total (new)** | 40-90s | From prompt to video |

---

## 🔮 Future Improvement Ideas

(See TEMPLATE_SYSTEM_OVERVIEW.md "Potential Improvements" section)

1. **Graph-based dependencies** - Full cycle detection
2. **Context passing** - Share state between micro-templates in composition
3. **Enhanced validation** - Per-template parameter schemas
4. **Streaming updates** - Real-time render progress
5. **Template versioning** - Hot-reload capability
6. **Visual editor** - GUI for building templates
7. **Multi-level caching** - Schema + code + video caching
8. **Better error messages** - Actionable validation feedback

---

## 📞 Key File Locations

| Feature | File | Line Range |
|---------|------|-----------|
| All 18 templates registered | engine.py | TEMPLATES dict |
| Main render function | engine.py | render_multi_scene_plan() |
| LLM planner | llm.py | generate_plan() |
| Full execution flow | tasks.py | render_graph_async() |
| Schema root | animation.py | AnimationPlan class |
| Generic interpreter | generic.py | GenericAnimationTemplate |

---

## ✅ Checklist: Understanding the System

- [ ] Read EXECUTIVE_SUMMARY.md (5 min)
- [ ] Read TEMPLATE_SYSTEM_OVERVIEW.md sections 1-3 (10 min)
- [ ] Review 3 code examples in QUICK_REFERENCE.md (5 min)
- [ ] Skim one template implementation (base.py + one domain template) (5 min)
- [ ] Read render_multi_scene_plan() in engine.py (5 min)
- [ ] Read generate_plan() in llm.py (5 min)
- [ ] Review render_graph_async() in tasks.py (5 min)
- [ ] View the architecture diagrams (Visual + Text)
- [ ] Review the decision tree for template selection
- [ ] Understand the 3 rendering modes

**Total: ~45 minutes to understand the complete system**

---

Generated: March 9, 2026
System Version: Current (as explored)
Documentation Scope: Complete architecture, templates, schemas, LLM, execution

