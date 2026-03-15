# Anima Studio - Template System Deep Dive

## Complete System Overview

### Architecture Flow Diagram

```
User Prompt
    ↓
[LLM Planner (Gemini)]
    - Rule-based concept router
    - Combined prompt with template registry
    - Validates against intent
    - Caches plan (Redis)
    ↓
[AnimationPlan DSL]
    - title, template, parameters
    - scenes: List[AnimationScene]
    - Each scene: objects + animations
    ↓
[Template Engine]
    - Domain-specific templates (Linear Algebra, Calculus, ML)
    - Micro-templates (primitives)
    - Generic fallback
    ↓
[Manim Code Generation]
    - Single or multi-scene output
    - Full Python class with construct()
    ↓
[Docker Render]
    - Copy script to container
    - Run: manim -qh scene.py Scene1 -o output.mp4
    - Copy video to outputs/
    ↓
[Video Output]
```

---

## 1. TEMPLATE STRUCTURE

### File Organization
```
backend/app/templates/
├── base.py                          # BaseTemplate ABC
├── engine.py                        # Template registry + render_multi_scene_plan()
├── generic.py                       # GenericAnimationTemplate (fallback)
├── primitives.py                    # Micro-templates (8 basic building blocks)
├── linear_algebra/
│   └── templates.py                 # MatrixMultiplication, VectorTransformation, Eigenvector, DotProduct
├── calculus/
│   └── templates.py                 # DerivativeTangent, IntegralArea, GradientDescent
├── machine_learning/
│   └── templates.py                 # NeuralNetwork, TransformerAttention
└── algorithms/
    └── templates.py                 # BFSTraversal
```

### Template Class Hierarchy

```python
BaseTemplate (ABC)
├── MatrixMultiplicationTemplate      [Linear Algebra]
├── VectorTransformationTemplate      [Linear Algebra]
├── EigenvectorTemplate               [Linear Algebra]
├── DotProductTemplate                [Linear Algebra]
├── DerivativeTangentTemplate         [Calculus]
├── IntegralAreaTemplate              [Calculus]
├── GradientDescentTemplate           [Calculus]
├── NeuralNetworkTemplate             [ML]
├── TransformerAttentionTemplate      [ML]
├── BFSTraversalTemplate              [Algorithms]
├── GenericAnimationTemplate          [Fallback]
├── DrawCurveTemplate                 [Micro]
├── PlacePointTemplate                [Micro]
├── DrawArrowTemplate                 [Micro]
├── HighlightObjectTemplate           [Micro]
├── DrawAxisTemplate                  [Micro]
├── WriteTextTemplate                 [Micro]
├── CreateVectorTemplate              [Micro]
└── TransformObjectTemplate           [Micro]
```

### BaseTemplate Implementation

```python
class BaseTemplate(ABC):
    """All 18 templates inherit from this."""
    
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.scene_name = "Scene1"
        self.background_color = "#0a0a0f"  # Dark background
    
    @abstractmethod
    def generate_construct_code(self) -> str:
        """Must return indented code for construct() method body.
        
        Returns lines like:
            "        self.play(Create(ax))\n"
            "        self.wait(1)\n"
        """
        pass
    
    def generate_code(self) -> str:
        """Full scene (header + imports + class + construct)."""
        return self.get_header() + self.get_class_def() + self.generate_construct_code()
    
    def get_header(self) -> str:
        """Returns: from manim import *\nconfig.background_color = ..."""
        pass
    
    def get_class_def(self) -> str:
        """Returns: class Scene1(Scene):\n    def construct(self):\n"""
        pass
```

---

## 2. SCHEMA DEFINITIONS

### AnimationPlan (DSL Root)

```python
class AnimationPlan(BaseModel):
    title: str                          # "Matrix Multiplication Explained"
    template: Optional[str]             # "matrix_multiplication" or "generic"
    parameters: Dict[str, Any]          # Varies by template type
    scenes: List[AnimationScene]        # Default: empty (access via parameters)
    
    @classmethod
    def create_fallback(cls, prompt: str = "Simple Animation") -> "AnimationPlan":
        """Create minimal valid plan with one simple scene."""
        # Returns: title="...", scenes=[AnimationScene("fallback", ...)]
```

### AnimationScene (Per-Scene Specification)

```python
class AnimationScene(BaseModel):
    scene_id: str                       # "intro", "mechanism", "result"
    description: Optional[str]          # "Show initial matrix"
    
    # SINGLE TEMPLATE MODE (legacy):
    template: Optional[str]             # "matrix_multiplication"
    
    # COMPOSITION MODE (new):
    templates: List[str]                # ["draw_curve", "place_point"]
    
    ### Dependency Management ###
    depends_on: List[str]               # ["intro"]  → scene execution order
    
    ### DSL Content (generic template) ###
    objects: List[AnimationObject]      # Create objects in scene
    animations: List[AnimationStep]     # Animate them
    
    ### Additional ###
    parameters: Dict[str, Any]          # Template-specific params
    narration: Optional[str]             # "Let me show you how..."
```

### AnimationObject (Primitive Objects)

```python
class AnimationObject(BaseModel):
    id: str                             # "curve1", "text_label"
    type: str                           # "circle" | "square" | "triangle" | "star" | "polygon"
                                        # "dot" | "text" | "vector" | "line" | "arrow"
    parameters: Dict[str, Any]          # Type-specific params:
                                        # circle: radius, color
                                        # text: text, font_size
                                        # vector: coords, color
                                        # line: start, end
                                        # arrow: start, end, color
```

### AnimationStep (Animation Actions)

```python
class AnimationStep(BaseModel):
    object_id: str                      # "circle1" → which object to animate
    action: str                         # "fade_in" | "fade_out" | "write" | "grow" | "move"
                                        # "scale" | "rotate" | "color" | "pulse" | 
                                        # "transform" | "follow_path"
    parameters: Dict[str, Any]          # Action-specific:
                                        # move: {to: [2, 0, 0]}
                                        # scale: {factor: 2.0}
                                        # rotate: {angle: 90}
                                        # color: {color: "YELLOW"}
                                        # transform: {target: "target_id"}
                                        # follow_path: {path: "circle"}
```

### UserIntent (Route Concept)

```python
class UserIntent(BaseModel):
    concept: str                        # "matrix_multiplication", "derivative_tangent"
    template: Optional[str]             # Pre-matched template (hint to LLM)
    parameters: Dict[str, Any]          # Pre-extracted params
    notes: str                          # Debug context
```

---

## 3. TEMPLATE ENGINE (engine.py)

### Template Registry

```python
TEMPLATES: Dict[str, Type[BaseTemplate]] = {
    # Linear Algebra (4)
    "matrix_multiplication": MatrixMultiplicationTemplate,
    "vector_transformation": VectorTransformationTemplate,
    "eigenvector": EigenvectorTemplate,
    "dot_product": DotProductTemplate,
    
    # Calculus (3)
    "derivative_tangent": DerivativeTangentTemplate,
    "integral_area": IntegralAreaTemplate,
    "gradient_descent": GradientDescentTemplate,
    
    # ML (2)
    "neural_network": NeuralNetworkTemplate,
    "transformer_attention": TransformerAttentionTemplate,
    
    # Algorithms (1)
    "bfs_traversal": BFSTraversalTemplate,
    
    # Fallbacks (1)
    "generic": GenericAnimationTemplate,
    
    # Micro-templates (8)
    "draw_curve": DrawCurveTemplate,
    "place_point": PlacePointTemplate,
    "draw_arrow": DrawArrowTemplate,
    "highlight_object": HighlightObjectTemplate,
    "draw_axis": DrawAxisTemplate,
    "write_text": WriteTextTemplate,
    "create_vector": CreateVectorTemplate,
    "transform_object": TransformObjectTemplate,
}
```

### Core Rendering Functions

#### `render_template(template_name, parameters, include_header=True) → str`
- Gets template class from registry
- Instantiates with parameters
- Calls `generate_construct_code()`
- Returns full code or just construct body

```python
# Usage:
manim_code = render_template("matrix_multiplication", {
    "matrix_a": [[1, 2], [3, 4]],
    "matrix_b": [[5, 6], [7, 8]]
})
```

#### `render_multi_scene_plan(plan: Dict) → str` ⭐ **MAIN RENDERER**

This is the workhorse function for DSL plans:

```python
def render_multi_scene_plan(plan: Dict[str, Any]) -> str:
    """
    Renders a multi-scene plan into a single Manim script.
    
    Key steps:
    1. Sort scenes by dependencies (_sort_scenes_by_dependency)
    2. Create single Scene1 class
    3. For each scene:
       - Check for templates[] list (composition mode)
       - If no list, use single template field
       - Render all template code
       - Add self.next_section() + self.wait(1) between scenes
    """
    
    # Output structure:
    # class Scene1(Scene):
    #     def construct(self):
    #         # Scene 1 code
    #         self.next_section()
    #         self.wait(1)
    #         
    #         # Scene 2 code
    #         self.next_section()
    #         self.wait(1)
```

**Key Features:**
- Single Scene1 class (Manim requirement)
- Multi-section layout (uses `self.next_section()`)
- Composition support: renders multiple templates per scene
- Dependency ordering via topological sort
- Automatic section breaks with 1-second wait

#### `_sort_scenes_by_dependency(scenes) → List[Dict]`

Simple topological sort:
```python
def _sort_scenes_by_dependency(scenes):
    """
    Reorder scenes so dependencies come first.
    
    Example:
    - scene_2: depends_on: ["scene_1"]
    - scene_1: depends_on: []
    → Output: [scene_1, scene_2]
    """
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
            visit(dep)  # Recursive: visit dependencies first
        result.append(scene)
    
    for s in scenes:
        visit(s["scene_id"])
    return result
```

---

## 4. ANIMATION OBJECT TYPES & ACTIONS

### Supported Object Types (GenericAnimationTemplate)

```python
Object Types               Manim Constructor              Parameters
─────────────────────────────────────────────────────────────────────
"circle"                  Circle(radius=r, color=c)      radius, color, position
"square"                  Square(color=c)                color, position
"triangle"                Triangle(color=c)              color, position
"star"                    Star(color=c)                  color, position
"polygon"                 RegularPolygon(n=sides)        sides, color, position
"dot"                     Dot(color=c)                   color, position
"text"                    Text(text, font_size=32)       text, font_size, position
"vector"                  Vector(coords)                 coords, color, position
"line"                    Line(start, end)               start, end, position
"arrow"                   Arrow(start, end)              start, end, color, position
```

### Supported Animation Actions (GenericAnimationTemplate)

```python
Action           Manim Code                         Parameters
──────────────────────────────────────────────────────────────
"fade_in"        self.play(FadeIn(obj))            none
"fade_out"       self.play(FadeOut(obj))           none
"write"          self.play(Write(obj))             none
"grow"           self.play(GrowFromCenter(obj))    none
"move"           self.play(obj.animate.move_to(pos))    to: [x, y, z]
"scale"          self.play(obj.animate.scale(f))       factor: float
"rotate"         self.play(Rotate(obj, angle))        angle: degrees
"color"          self.play(obj.animate.set_color(c))  color: "YELLOW"
"pulse"          self.play(Indicate(obj))           none
"transform"      self.play(ReplacementTransform(...)) target: "target_id"
"follow_path"    self.play(MoveAlongPath(obj, path))  path: "circle"|"line"
```

---

## 5. LLM PLANNER SYSTEM (llm.py)

### Planning Pipeline

```
generate_plan(user_prompt: str) → AnimationPlan
    ↓
    1️⃣ Check Redis Cache (key: f"plan_v2:{md5(prompt)}")
       Hit → Return cached plan
       Miss → Continue
    ↓
    2️⃣ rule_based_concept_router(prompt: str) → Optional[UserIntent]
       Detect: "matrix multiply" → matrix_multiplication hint
               "derivative" → derivative_tangent hint
               "neural" → neural_network hint
    ↓
    3️⃣ call_combined_llm_planner(prompt, hint) → AnimationPlan
       Single Gemini API call with:
       - Template registry list
       - DSL primitives (objects, actions)
       - Scene graph rules
       - Required JSON format
       ↓
       LLM Response: {intent: {...}, plan: {title, template, scenes: [...]}}
    ↓
    4️⃣ validate_plan_against_intent(plan, intent) → List[str]
       Check: - Template exists in registry
              - Scene count ≤ 6
              - Scenes in parameters (if generic template)
       Return violations list
    ↓
    5️⃣ repair_plan(prompt, intent, violations) → AnimationPlan
       If violations detected:
       - Second LLM call to fix issues
       - Return repaired plan (or original if repair fails)
    ↓
    6️⃣ Cache Result
       redis.setex(cache_key, 3600*24, plan_json)
    ↓
    Return AnimationPlan
```

### Combined LLM Prompt

The `COMBINED_PLANNER_PROMPT` template:

```
"You are a Master 3Blue1Brown Animation Planner.
Decompose a mathematical concept into a SCENE GRAPH and DSL parameters.

AVAILABLE TEMPLATES:
- matrix_multiplication
- vector_transformation
- ... (full list auto-injected)

MICRO-TEMPLATES (for composition):
- draw_curve, place_point, draw_arrow, highlight_object

DSL PRIMITIVES:
Objects: circle, square, triangle, star, polygon, dot, text, vector, line, arrow
Actions: fade_in, fade_out, write, grow, move, scale, rotate, color, follow_path, transform

SCENE GRAPH RULES:
1. Break request into 3-5 scenes (Intro → Intuition → Mechanism → Result)
2. Use 'depends_on' to specify scene order
3. Use 'templates' list to COMPOSE multiple micro-templates in one scene
4. If no specialized template, use 'generic' with objects/animations
5. Output STRICT JSON only

REQUIRED OUTPUT FORMAT:
{
  "intent": {
    "concept": "concept_name",
    "notes": "storytelling strategy"
  },
  "plan": {
    "title": "Animation Title",
    "template": "template_name_or_generic",
    "parameters": {
      "scenes": [
        {
          "scene_id": "intro",
          "description": "...",
          "depends_on": [],
          "templates": ["draw_curve", "place_point"],
          "parameters": {"expression": "x**2", ...},
          "narration": "..."
        },
        ...
      ]
    }
  }
}

User request: {user_prompt}
"
```

### Configuration

```python
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))  # Low temperature
REDIS_URL = "redis://redis:6379"

# Safety Settings (all disabled)
HarmCategory.HARASSMENT: BLOCK_NONE
HarmCategory.HATE_SPEECH: BLOCK_NONE
HarmCategory.SEXUALLY_EXPLICIT: BLOCK_NONE
HarmCategory.DANGEROUS_CONTENT: BLOCK_NONE
```

### Key Functions

#### `rule_based_concept_router(prompt) → Optional[UserIntent]`
```python
if "matrix" in p and "multiply" in p:
    return UserIntent(concept="matrix_multiplication", 
                     template="matrix_multiplication")
if "derivative" in p or "tangent" in p:
    return UserIntent(concept="derivative_tangent", 
                     template="derivative_tangent")
```

#### `call_combined_llm_planner(prompt, hint) → AnimationPlan`
```python
# Inject template registry into prompt dynamically
template_info = "\n".join([f"- {name}" for name in AVAILABLE_TEMPLATES.keys()])
full_prompt = COMBINED_PLANNER_PROMPT.format(
    template_info=template_info,
    user_prompt=user_prompt
)

response = model.generate_content(full_prompt, timeout=30)
data = json.loads(_extract_json(response.text))
return AnimationPlan(**data["plan"])
```

#### `validate_plan_against_intent(plan, intent, prompt) → List[str]`
```python
violations = []

# Check template exists
if plan.template and plan.template not in AVAILABLE_TEMPLATES:
    violations.append(f"Unknown template: {plan.template}")

# Check scene structure
if plan.template == "generic":
    scenes = plan.parameters.get("scenes", [])
    if not scenes:
        violations.append("Generic template must have 'scenes'")
    if len(scenes) > 6:
        violations.append(f"Too many scenes: {len(scenes)}")

return violations
```

---

## 6. EXECUTION LAYER (tasks.py)

### Render Graph Pipeline (`render_graph_async`)

```python
async def render_graph_async(job_id: str) → {"status": "success"|"failed", "video_filename": str}:
    """Main rendering pipeline for LLM-generated plans."""
    
    try:
        # 1. Get job from database
        job = await db.fetch(Job).where(id == job_id)
        prompt = job.prompt
        
        # 2. Generate DSL Plan
        plan = generate_plan(prompt)
        # → Calls LLM planner with caching
        
        # 3. Update job with plan
        await db.update(job, plan_json=plan.model_dump())
        
        # 4. Convert Plan to Manim Code
        if plan.template:
            if plan.parameters.get("scenes"):
                manim_code = render_multi_scene_plan(plan.model_dump())
                # Multi-scene plan rendering
            else:
                manim_code = render_template(plan.template, plan.parameters)
                # Single template rendering
        else:
            manim_code = generate_manim_code(prompt)
            # Fallback: direct Gemini code generation
        
        # 5. Render in Docker
        # Copy script to container
        docker exec anima_manim_renderer bash -c "cat > /manim/scene.py" < manim_code
        
        # Run Manim
        docker exec anima_manim_renderer manim -qh /manim/scene.py Scene1 -o {job_id}.mp4
        
        # Copy output
        docker exec anima_manim_renderer bash -c "cp /manim/media/videos/scene/1080p60/{job_id}.mp4 /manim/outputs/"
        
        # 6. Update job with success
        await db.update(job, status=SUCCEEDED, video_filename="{job_id}.mp4", code=manim_code, logs=[...])
        
        return {"status": "success", "video_filename": "{job_id}.mp4"}
        
    except Exception as e:
        await db.update(job, status=FAILED, error=str(e), logs=[...])
        return {"status": "failed", "error": str(e)}
```

### Flow Visualization

```
DB (Job with prompt)
    ↓
generate_plan(prompt)
    ├→ Check Redis cache
    ├→ rule_based_concept_router
    └→ Gemini LLM call → AnimationPlan DSL
              ↓
         animate_plan = {
           title: "...",
           template: "matrix_multiplication",
           parameters: {
             scenes: [
               {scene_id: "intro", ...},
               {scene_id: "mechanism", depends_on: ["intro"], ...}
             ]
           }
         }
    ↓
render_multi_scene_plan(plan)
    ├→ Sort scenes by dependency
    ├→ Create Scene1 class
    ├→ Render each scene's templates
    └→ Return full Python code
    ↓
manim_code = """
from manim import *
config.background_color = '#0a0a0f'

class Scene1(Scene):
    def construct(self):
        # Intro scene
        matrix_a = [[1, 2], [3, 4]]
        ...
        self.next_section()
        self.wait(1)
        
        # Mechanism scene
        ...
        self.next_section()
        self.wait(1)
"""
    ↓
[Docker Container]
- Write script to /manim/scene.py
- Execute: manim -qh /manim/scene.py Scene1 -o output.mp4
- Copy video to /manim/outputs/
    ↓
Update Job (DB)
- status: SUCCEEDED
- video_filename: "job_id.mp4"
- code: manim_code
- logs: [...]
```

### Docker Integration

```bash
# Step 1: Copy script into container
docker exec -i anima_manim_renderer bash -c "cat > /manim/scene.py" < python_code

# Step 2: Render animation
docker exec anima_manim_renderer \
  manim -qh /manim/scene.py Scene1 -o output.mp4

# Flags:
# -q: quality (h = high = 1080p60)
# -o: output filename

# Step 3: Copy video to host
docker exec anima_manim_renderer \
  bash -c "cp /manim/media/videos/scene/1080p60/output.mp4 /manim/outputs/"
```

---

## 7. TEMPLATE EXAMPLES

### Example 1: Matrix Multiplication (Domain-Specific)

**Input Plan:**
```json
{
  "title": "Matrix Multiplication",
  "template": "matrix_multiplication",
  "parameters": {
    "matrix_a": [[1, 2], [3, 4]],
    "matrix_b": [[5, 6], [7, 8]]
  }
}
```

**Generated Code:**
```python
from manim import *
config.background_color = '#0a0a0f'

class Scene1(Scene):
    def construct(self):
        # 3B1B Matrix Multiplication Pattern
        matrix_a_val = [[1, 2], [3, 4]]
        matrix_b_val = [[5, 6], [7, 8]]
        
        m1 = Matrix(matrix_a_val).scale(0.8).to_edge(LEFT, buff=1)
        m2 = Matrix(matrix_b_val).scale(0.8).next_to(m1, RIGHT, buff=0.5)
        equals = MathTex('=')
        
        import numpy as np
        res_val = np.dot(np.array(matrix_a_val), np.array(matrix_b_val)).tolist()
        m3 = Matrix(res_val).scale(0.8).next_to(equals, RIGHT, buff=0.5)
        group = VGroup(m1, m2, equals, m3).center()
        
        self.play(Write(m1), Write(m2))
        self.wait(1)
        self.play(Write(equals), Write(m3))
        self.wait(2)
```

### Example 2: Composition Mode (Multi-Template)

**Input Plan:**
```json
{
  "title": "Derivative Visualization",
  "template": null,
  "parameters": {
    "scenes": [
      {
        "scene_id": "curve",
        "templates": ["draw_curve", "place_point"],
        "parameters": {
          "expression": "x**2",
          "x": 1,
          "color": "BLUE"
        }
      }
    ]
  }
}
```

**Generated Code:**
```python
class Scene1(Scene):
    def construct(self):
        # --- Scene: curve ---
        # Draw curve template
        ax = Axes()
        curve = ax.plot(lambda x: x**2, color=BLUE)
        self.play(Create(ax), Create(curve))
        
        # Place point template
        # Assuming 'ax' and 'curve' exist in scope
        point = Dot(ax.c2p(1, 1**2), color=YELLOW)
        self.play(FadeIn(point))
        
        self.next_section()
        self.wait(1)
```

### Example 3: Generic DSL Mode

**Input Plan:**
```json
{
  "title": "Bouncing Circle",
  "template": "generic",
  "parameters": {
    "scenes": [
      {
        "scene_id": "bounce",
        "objects": [
          {"id": "circle1", "type": "circle", "parameters": {"radius": 0.5, "color": "BLUE"}}
        ],
        "animations": [
          {"object_id": "circle1", "action": "move", "parameters": {"to": [2, 0, 0]}},
          {"object_id": "circle1", "action": "move", "parameters": {"to": [0, 0, 0]}}
        ]
      }
    ]
  }
}
```

**Generated Code:**
```python
class Scene1(Scene):
    def construct(self):
        # Generic Primitive Animation Sequence
        # Scene: bounce
        # Create objects
        circle1 = Circle(radius=0.5, color=BLUE)
        circle1.move_to([0, 0, 0])
        
        # Run animations
        self.play(circle1.animate.move_to([2, 0, 0]))
        self.play(circle1.animate.move_to([0, 0, 0]))
        
        self.wait(1)
```

---

## 8. SCENE DEPENDENCY SYSTEM

### How `depends_on` Works

```python
# Plan with dependencies:
scenes = [
    {"scene_id": "step2", "depends_on": ["step1"], "template": "..."},
    {"scene_id": "step1", "depends_on": [], "template": "..."},
    {"scene_id": "step3", "depends_on": ["step2", "step1"], "template": "..."},
]

# After _sort_scenes_by_dependency():
# Output: [step1, step2, step3]

# In output class:
class Scene1(Scene):
    def construct(self):
        # Step 1 (no deps)
        ...
        self.next_section()
        self.wait(1)
        
        # Step 2 (depends on step 1)
        ...
        self.next_section()
        self.wait(1)
        
        # Step 3 (depends on step 2 and step 1)
        ...
```

---

## 9. COMPOSITION MODE DETAILS

### How `templates[]` List Works

When a scene has a `templates` list:

```python
# Input:
{
  "scene_id": "complex",
  "templates": ["draw_axis", "draw_curve", "place_point"],
  "parameters": {...}
}

# render_multi_scene_plan() does:
for template_name in ["draw_axis", "draw_curve", "place_point"]:
    template_code = render_template(template_name, scene.parameters, include_header=False)
    # Concatenate all body code
    scene_code += template_code

# Output: All three animations rendered sequentially within same section
```

**Limitations:**
- Each micro-template renders independently
- No shared state between templates
- Objects created in one template visible to next (if in same construct)
- Must coordinate via shared parameter names

---

## 10. FALLBACK STRATEGIES

### Priority Order

```
1. Check Plan Cache (Redis)
   └─ Hit: Return cached AnimationPlan

2. Domain-Specific Template Match
   └─ matrix_multiplication, derivative_tangent, etc.
   └─ Fast, predictable output

3. Composition Mode
   └─ Multiple micro-templates combined

4. Generic Template
   └─ Interpret objects[] + animations[] arrays
   └─ Most flexible but verbose

5. Full LLM Codegen (Fallback)
   └─ generate_manim_code() with direct Gemini call
   └─ Last resort

6. Minimal Fallback
   └─ AnimationPlan.create_fallback()
   └─ Single "Hello World" text animation
   └─ Used only if LLM call fails
```

### Error Handling

```python
try:
    plan = generate_plan(user_prompt)
except Exception as e:
    logger.error(f"Plan generation failed: {e}")
    return AnimationPlan.create_fallback(user_prompt)

# In render_graph_async:
try:
    render in Docker...
except subprocess.TimeoutExpired:
    retry up to 3 times with backoff
except Exception as e:
    Update job with FAILED status
    Return error message
```

---

## 11. KEY INSIGHTS & PATTERNS

### Multi-Scene Architecture
- Single `Scene1` class with multiple sections
- Uses `self.next_section()` to split logical scenes
- `self.wait(1)` pause between sections

### Composition Pattern
- Micro-templates provide reusable building blocks
- Combine via `templates: List[str]`
- Enables modular animation construction

### Dependency Management
- `depends_on` field orders scenes topologically
- Ensures prerequisites render before dependents
- Simple DFS-based topological sort

### Caching Strategy
- LLM plans cached in Redis (24h)
- Avoids redundant Gemini API calls
- Key: `plan_v2:{md5(prompt)}`

### Safety & Fallback
- Redis cache miss → LLM call → cached result
- Plan validation → repair loop on violations
- Multiple rendering fallback options
- Graceful degradation to "Hello World"

---

## 12. LIMITATIONS & FUTURE IMPROVEMENTS

### Current Limitations
1. **State Sharing**: Micro-templates don't share state
2. **Cycle Detection**: Dependency sort doesn't check for cycles
3. **Validation**: Basic checks only (template exists, scene count)
4. **Performance**: Every unique prompt hits LLM once (then cached)
5. **Composition**: Linear concatenation, no intelligent sequencing
6. **Error Messages**: Limited validation feedback to LLM for repair

### Potential Improvements
1. Graph-based dependency system with cycle detection
2. Context passing between micro-templates in composition mode
3. Expanded validation with auto-repair suggestions
4. Template parameter validation schemas
5. Caching at multiple levels (schema, code, video)
6. Streaming render progress updates
7. Template versioning and hot-reload
8. Visual template playground/editor

---

## 13. QUICK REFERENCE TABLE

| Concept | Location | Purpose |
|---------|----------|---------|
| `BaseTemplate` | `base.py` | Abstract base for all 18 templates |
| `AnimationPlan` | `schemas/animation.py` | DSL root structure |
| `AnimationScene` | `schemas/animation.py` | Per-scene specification |
| `render_template()` | `engine.py` | Convert template → code |
| `render_multi_scene_plan()` | `engine.py` | Convert plan → full script |
| `generate_plan()` | `llm.py` | LLM planner with caching |
| `render_graph_async()` | `tasks.py` | Full rendering pipeline |
| TEMPLATES registry | `engine.py` | 18 template classes |
| Micro-templates | `primitives.py` | 8 building blocks |
| Domain templates | `{domain}/templates.py` | 10 specialized animations |
| Generic fallback | `generic.py` | DSL interpreter |

