"""LLM service for generating animation plans using Google Gemini with intent validation."""

import hashlib
import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import redis
from google.generativeai.types import HarmBlockThreshold, HarmCategory

try:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
except Exception:
    torch = None
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None

from app.core.config import settings
from app.schemas.animation import AnimationObject, AnimationPlan, AnimationScene, AnimationStep
from app.schemas.intent import UserIntent
from app.services.narration import NarrationPipeline
from app.templates.capabilities import get_capability_registry
from app.templates.engine import TEMPLATES as AVAILABLE_TEMPLATES

logger = logging.getLogger(__name__)

# Redis for plan caching
redis_client = redis.Redis.from_url(settings.REDIS_URL)


class LLMQuotaExceededError(Exception):
    """Raised when the LLM fails due to quota or token limits."""


# Configuration from environment
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if LLM_PROVIDER == "gemini":
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY environment variable is not set!")
    else:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")

LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Mandatory T5 prompt enhancement for stronger intent understanding.
T5_MODEL_NAME = os.getenv("T5_MODEL_NAME", "google/flan-t5-small")
T5_MAX_INPUT_TOKENS = int(os.getenv("T5_MAX_INPUT_TOKENS", "384"))
T5_MAX_NEW_TOKENS = int(os.getenv("T5_MAX_NEW_TOKENS", "192"))
T5_ENHANCED_CONTEXT_MAX_CHARS = int(os.getenv("T5_ENHANCED_CONTEXT_MAX_CHARS", "720"))
T5_STRUCTURED_ENABLED = os.getenv("T5_STRUCTURED_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
T5_STRUCTURED_TASK_PREFIX = os.getenv(
    "T5_STRUCTURED_TASK_PREFIX",
    "translate English to graph JSON: ",
)
T5_STRUCTURED_MAX_NEW_TOKENS = int(os.getenv("T5_STRUCTURED_MAX_NEW_TOKENS", "96"))

_SAFE_PLOT_COLOR_TOKENS = {
    "BLUE",
    "BLUE_C",
    "BLUE_D",
    "GREEN",
    "GREEN_C",
    "TEAL",
    "YELLOW",
    "GOLD",
    "RED",
    "MAROON",
    "ORANGE",
    "PURPLE",
    "WHITE",
}

_SAFE_EXPR_TOKEN_PATTERN = re.compile(r"[A-Za-z_]+")
_SAFE_NUMERIC_EXPR_PATTERN = re.compile(r"^[0-9eE\+\-\*/\(\)\.,\s]*$")
_PLOT_DEFAULT_X_RANGE = [0.0, 2.0 * math.pi]
_PLOT_DEFAULT_Y_RANGE = [-3.0, 3.0]

_T5_INITIALIZED = False
_T5_TOKENIZER: Any = None
_T5_MODEL: Any = None
_T5_INIT_ERROR: Optional[str] = None

# Combined Visual Reasoning + DSL Planner prompt with Phase 2 Templates
# Enhanced with logic inspired by high-quality Manim generators
COMBINED_PLANNER_PROMPT = """You are a senior Manim animator and pedagogical expert. 
Your task is to transform complex mathematical and scientific concepts into clear, beautiful animations.

CORE DIRECTIVES:
1.  **Pedagogical Depth**: Don't just show the answer. Show the *process*.
2.  **Visual Clarity**: Use high-contrast colors and proper spacing.
3.  **Logical Flow**: Every animation must follow a logical sequence: Setup -> Action -> Result -> Insight.
4.  **Visual Styles**: Choose an appropriate style based on the user's intent.

VISUAL STYLE PRESETS:
- 3b1b (Default): High-contrast, dark background, yellow/blue accents. Best for mathematical deep dives.
- modern: Light background, vibrant blues and pinks, rounded aesthetics. Best for tech/modern concepts.
- minimalist: Extremely clean, monochromatic with subtle accents. Best for professional/corporate presentations.
- dark: Pure black background, stark white/red accents. Best for high-impact or dramatic explanations.

AVAILABLE PHASE 2 TEMPLATES:
- matrix_multiplication: Step-by-step dot product visualization with row/column highlighting.
- eigenvector: Shows linear transformation, scaling, and the stable direction of eigenvectors.
- vector_transformation: Geometric transformation of vectors.
- derivative_slope: Visualizes the tangent line approaching the derivative (f'(x)).
- integral_accumulation: Visualizes Riemann sums and area under curve (∫f(x)dx).
- unit_circle: Visualizes sin/cos projections on a rotating unit circle.
- trig_waves: Generates sine/cosine waves from a rotating unit circle.
- sorting: Visualizes sorting algorithms (like bubble sort) using bars.
- dijkstra: Visualizes shortest path in a weighted graph.
- bfs_dfs_comparison: Side-by-side comparison of BFS and DFS traversal orders.
- graph_visualization: Visualizes graph structures such as Markov chains.
- neural_network / backpropagation / convolution_filters: Visualize ML training pipelines.
- transformer_attention / embedding_space: Visualize LLM token and embedding flow.
- mnist_recognition: End-to-end MNIST pipeline (digit input -> feature extraction -> class probabilities).

SCENE GRAPH COMPOSITION:
- Break the explanation into 3-6 distinct scenes.
- Use 'depends_on' to maintain state across scenes.
- Use 'templates' list to combine multiple micro-actions.

TEMPLATE-FREE SAFE MODE (for NEW/UNSEEN topics):
- If no template clearly fits, set plan.template to null and use scenes with template="generic".
- Use only safe generic object types: text, math_tex, matrix, arrow, line, axes, circle, rectangle, dot, image, token, node, state.
- Use only safe actions: write, fade_in, fade_out, create, move, scale, rotate, color, highlight, indicate, transform, connect, wait.
- Every animation.object_id MUST reference an object id that exists in the same scene.
- Keep object ids as Python-safe identifiers: letters, numbers, underscore only (no spaces or hyphens).

STRICT JSON FORMAT:
{{
  "intent": {{ "concept": "name", "difficulty": "beginner|intermediate|advanced" }},
  "plan": {{
    "title": "Professional Title",
    "style": "3b1b|modern|minimalist|dark",
    "scenes": [
      {{
        "scene_id": "intro",
        "template": "generic",
        "objects": [ 
          {{ "id": "t1", "type": "text", "parameters": {{ "text": "REPLACE_WITH_TOPIC", "position": [0, 3, 0] }} }} 
        ],
        "animations": [ {{ "object_id": "t1", "action": "write" }} ],
        "narration": "REPLACE_WITH_INTRO"
      }},
      {{
        "scene_id": "core",
        "depends_on": ["intro"],
        "template": "chosen_template",
        "parameters": {{ ... }},
        "narration": "REPLACE_WITH_EXPLANATION"
      }}
    ]
  }}
}}

REFINE MODE:
If you are provided with an existing plan and a refinement request, your goal is to modify the existing plan while keeping its structure intact where possible.
Refinement examples:
- "Change the background to white" -> Change "style" to "modern"
- "Make the labels bigger" -> Update "parameters" of text objects
- "Add a scene explaining the result" -> Append a new scene to the "scenes" list

CRITICAL: 
- RESPONSE MUST BE JSON ONLY.
- DO NOT INCLUDE ANY PREAMBLE OR POSTAMBLE TEXT.
- ALL NUMERIC PARAMETERS MUST BE CONCRETE NUMBERS, NEVER SYMBOLIC VARIABLE NAMES.
  For example, use "radius": 1.0 NOT "radius": "r". Use "side_length": 2.0 NOT "side_length": "a".
  If the prompt says "radius r", pick a sensible default like 1.0 or 2.0.
- NEVER USE UNDEFINED PYTHON VARIABLES in object parameters or expression strings.
  Expressions must only use x (the curve variable), constants, and numpy functions (np.sin, np.pi, etc).
- FOR TRIGONOMETRY: Always use 'unit_circle' to explain sine/cosine fundamentally.
- FOR EIGENVECTORS: Use 'eigenvector'.
- FOR ALGEBRA OR SYSTEMS OF EQUATIONS: Use 'generic' with math_tex objects and matrix/determinant steps.
- FOR CALCULUS: Use 'derivative_slope' for tangents or 'integral_accumulation' for areas.
- FOR TOKENIZATION/LLMs: Prefer 'transformer_attention' and optionally 'embedding_space'.
- FOR MARKOV CHAINS: Prefer 'graph_visualization'.
- FOR BFS vs DFS comparisons: Prefer 'bfs_dfs_comparison'.
- FOR MNIST DIGIT RECOGNITION: Prefer 'mnist_recognition'.
- ENSURE ALL MATRICES AND FORMULAS ARE MATHEMATICALLY CORRECT.

PEDAGOGICAL PATTERNS:
- Algebra: Equation -> Step-by-step manipulation -> Balanced transformation -> Solution.
- Derivatives: Curve -> Point -> Tangent line -> Slope calculation -> f'(x).
- Integrals: Curve -> Riemann rectangles -> Limit as Δx -> 0 -> Area accumulation -> ∫f(x)dx.
- Matrix: Matrices -> Row/Column dot products -> Highlight intermediate sums -> Result.
- Trig: Unit Circle -> Rotating radius -> Projections on axes -> Wave generation.
- Algorithms: Data structure (Bars/Graph) -> Rule application (Compare/Edge weight) -> State update -> Final sorted/visited state.

User request: {user_prompt}
"""


_SAFE_GENERIC_OBJECT_TYPES = {
    "text",
    "label",
    "math_tex",
    "mathtex",
    "latex",
    "formula",
    "equation",
    "matrix",
    "determinant",
    "vector",
    "line",
    "arrow",
    "dot",
    "circle",
    "square",
    "rectangle",
    "triangle",
    "polygon",
    "ellipse",
    "hexagon",
    "axes",
    "axis",
    "coordinate_system",
    "number_line",
    "numberline",
    "brace",
    "image",
    "mnist_image",
    "digit_image",
    "token",
    "word",
    "subword",
    "state",
    "markov_state",
    "node",
    "graph_node",
    "neural_network",
    "backpropagation",
    "cube",
    "box",
    "rectangular_prism",
    "sphere",
    "ball",
    "cylinder",
    "cone",
    "torus",
    "donut",
    "surface",
    "3d_surface",
    "parametric_surface",
    "3d_axes",
    "threedaxes",
    "3d_coordinate_system",
}

_OBJECT_TYPE_ALIASES = {
    "equation_text": "math_tex",
    "equationtex": "math_tex",
    "formula_text": "math_tex",
    "graph": "node",
    "network": "neural_network",
    "dataset": "text",
    "feature_map": "rectangle",
    "attention_head": "token",
}

_SAFE_GENERIC_ACTIONS = {
    "fade_in",
    "fade_out",
    "write",
    "grow",
    "move",
    "scale",
    "rotate",
    "color",
    "pulse",
    "highlight",
    "indicate",
    "create",
    "draw",
    "show",
    "wait",
    "transform",
    "connect",
    "follow_path",
}

_ACTION_ALIASES = {
    "appear": "fade_in",
    "show_up": "fade_in",
    "reveal": "fade_in",
    "disappear": "fade_out",
    "hide": "fade_out",
}

_ADVANCED_RENDER_HINTS = {
    "complex",
    "advanced",
    "production",
    "professional",
    "detailed",
    "in depth",
    "in-depth",
    "deep dive",
    "high quality",
    "cinematic",
    "very good",
    "not simple",
}

_HIGH_FRAME_HINTS = {
    "more frames",
    "high fps",
    "higher fps",
    "60fps",
    "60 fps",
    "smooth",
    "fluid",
}

_CONCISE_RENDER_HINTS = {
    "quick",
    "brief",
    "short",
    "simple",
    "minimal",
}


def _load_t5_preprocessor() -> tuple[Any, Any]:
    """Load T5 artifacts once and reuse across requests."""
    global _T5_INITIALIZED, _T5_TOKENIZER, _T5_MODEL, _T5_INIT_ERROR

    if _T5_INITIALIZED:
        if _T5_INIT_ERROR:
            raise RuntimeError(_T5_INIT_ERROR)
        return _T5_TOKENIZER, _T5_MODEL

    if AutoTokenizer is None or AutoModelForSeq2SeqLM is None:
        _T5_INIT_ERROR = "T5 input preprocessor is mandatory but transformers/torch are unavailable"
        _T5_INITIALIZED = True
        raise RuntimeError(_T5_INIT_ERROR)

    try:
        _T5_TOKENIZER = AutoTokenizer.from_pretrained(T5_MODEL_NAME)
        _T5_MODEL = AutoModelForSeq2SeqLM.from_pretrained(T5_MODEL_NAME)
        _T5_MODEL.eval()
        _T5_INIT_ERROR = None
        _T5_INITIALIZED = True
        logger.info("Mandatory T5 input preprocessor enabled", extra={"model": T5_MODEL_NAME})
    except Exception as e:
        _T5_INIT_ERROR = f"Failed to initialize mandatory T5 preprocessor: {e}"
        _T5_TOKENIZER = None
        _T5_MODEL = None
        _T5_INITIALIZED = True
        raise RuntimeError(_T5_INIT_ERROR) from e

    return _T5_TOKENIZER, _T5_MODEL


def _compact_prompt_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _trim_prompt_text(value: str, max_chars: int) -> str:
    compact = _compact_prompt_text(value)
    if len(compact) <= max_chars:
        return compact

    clipped = compact[: max(0, max_chars)].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return f"{clipped}..."


def _merge_prompt_with_enhancement(user_prompt: str, enhanced_prompt: str) -> str:
    """Build a planner-facing prompt that preserves the original request and adds enrichment."""
    original = _compact_prompt_text(user_prompt)
    enhanced = _trim_prompt_text(enhanced_prompt, T5_ENHANCED_CONTEXT_MAX_CHARS)

    if not original:
        return enhanced
    if not enhanced:
        return original
    if enhanced.lower() == original.lower():
        return original

    return (
        "Authoritative user request (must be preserved exactly):\n"
        f"{original}\n\n"
        "Enhancement notes for richer animation (use these to improve scene depth, visual "
        "staging, transitions, and pedagogy without dropping any user detail):\n"
        f"{enhanced}"
    )


def _normalize_prompt_with_t5(user_prompt: str) -> tuple[str, Dict[str, Any]]:
    """Enhance raw user text for planning while preserving all technical meaning."""
    cleaned_prompt = _compact_prompt_text(user_prompt)
    meta: Dict[str, Any] = {
        "required": True,
        "executed": False,
        "applied": False,
        "model": T5_MODEL_NAME,
        "mode": "enhance_preserve",
    }

    if not cleaned_prompt:
        meta["reason"] = "empty_prompt"
        return cleaned_prompt, meta

    meta["source_prompt"] = cleaned_prompt[:400]

    tokenizer, model = _load_t5_preprocessor()

    instruction = (
        "Enhance this educational animation request for a planning model.\n"
        "Do not summarize and do not remove any concrete detail.\n"
        "Preserve equations, numbers, constraints, style preferences, examples, and scope.\n"
        "Add actionable animation guidance for scene flow, visual emphasis, transitions, "
        "pacing, and pedagogical checkpoints.\n"
        "Return only the enhanced brief text.\n"
        f"Request: {cleaned_prompt}"
    )
    try:
        encoded = tokenizer(
            instruction,
            return_tensors="pt",
            truncation=True,
            max_length=T5_MAX_INPUT_TOKENS,
        )
        generation_kwargs = {
            "max_new_tokens": T5_MAX_NEW_TOKENS,
            "num_beams": 4,
            "do_sample": False,
            "early_stopping": True,
            "no_repeat_ngram_size": 3,
        }

        if torch is not None:
            with torch.no_grad():
                output_ids = model.generate(**encoded, **generation_kwargs)
        else:
            output_ids = model.generate(**encoded, **generation_kwargs)

        meta["executed"] = True
        rewritten_prompt = _compact_prompt_text(
            tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        )

        if rewritten_prompt:
            meta["text"] = rewritten_prompt

        if rewritten_prompt and rewritten_prompt.lower() != cleaned_prompt.lower():
            meta["applied"] = True
            return rewritten_prompt, meta

        if rewritten_prompt:
            meta["reason"] = "no_change"
            return rewritten_prompt, meta

        meta["reason"] = "empty_output"
        return cleaned_prompt, meta
    except Exception as e:
        logger.error(f"Mandatory T5 prompt normalization failed: {e}")
        raise RuntimeError(f"Mandatory T5 prompt normalization failed: {e}") from e


def _safe_eval_numeric_expression(raw_value: Any, default: float) -> float:
    """Safely evaluate very small arithmetic expressions (e.g. 2*pi)."""
    if isinstance(raw_value, (int, float)):
        return float(raw_value)

    expr = str(raw_value or "").strip().lower()
    if not expr:
        return default

    # Handle implicit multiplication in numeric ranges, e.g. 2pi or (1+1)pi.
    expr = re.sub(r"(?<=\d)(?=[A-Za-z(])", "*", expr)
    expr = re.sub(r"(?<=\))(?=[A-Za-z0-9(])", "*", expr)
    expr = expr.replace("tau", str(2.0 * math.pi)).replace("pi", str(math.pi))
    expr = expr.replace("^", "**")
    if not _SAFE_NUMERIC_EXPR_PATTERN.match(expr):
        return default

    try:
        return float(eval(expr, {"__builtins__": {}}, {}))  # nosec B307 - validated numeric grammar
    except Exception:
        return default


def _coerce_range(value: Any, default: List[float]) -> List[float]:
    """Convert range payload into a safe [min, max] list of floats."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            parts = [p.strip() for p in stripped[1:-1].split(",")]
        else:
            parts = [p.strip() for p in stripped.split(",") if p.strip()]
    elif isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        parts = []

    if len(parts) < 2:
        return list(default)

    start = _safe_eval_numeric_expression(parts[0], default[0])
    end = _safe_eval_numeric_expression(parts[1], default[1])
    if end <= start:
        end = start + max(1.0, abs(default[1] - default[0]))
    return [round(start, 4), round(end, 4)]


def _sanitize_plot_expression(raw_expression: Any) -> Optional[str]:
    """Normalize a function expression into a safe NumPy expression for templates."""
    expr = str(raw_expression or "").strip()
    if not expr:
        return None

    expr = re.sub(r"^(?:y|f\(x\))\s*=\s*", "", expr, flags=re.IGNORECASE)
    expr = expr.replace("^", "**")
    expr = re.sub(r"\s+", "", expr)
    # Handle implicit multiplication forms like 2sin(3x), 3x, (x+1)(x-1).
    expr = re.sub(r"(?<=\d)(?=[A-Za-z(])", "*", expr)
    expr = re.sub(r"(?<=\))(?=[A-Za-z0-9(])", "*", expr)

    # Standardize common functions and constants.
    replacements = {
        "sin": "np.sin",
        "cos": "np.cos",
        "tan": "np.tan",
        "sqrt": "np.sqrt",
        "log": "np.log",
        "exp": "np.exp",
        "abs": "np.abs",
    }
    for src, dst in replacements.items():
        expr = re.sub(rf"\b{src}\b", dst, expr)

    expr = re.sub(r"\bpi\b", "np.pi", expr)

    if not re.fullmatch(r"[A-Za-z0-9_\+\-\*/\(\)\.,]+", expr):
        return None

    allowed_tokens = {
        "x",
        "np",
        "sin",
        "cos",
        "tan",
        "sqrt",
        "log",
        "exp",
        "abs",
        "pi",
    }
    for token in _SAFE_EXPR_TOKEN_PATTERN.findall(expr):
        if token not in allowed_tokens:
            return None

    return expr


def _canonical_plot_color(raw_color: Any) -> str:
    c = str(raw_color or "BLUE").strip().upper().replace(" ", "_")
    return c if c in _SAFE_PLOT_COLOR_TOKENS else "BLUE"


def _parse_t5_structured_output(raw_output: str) -> Optional[Dict[str, Any]]:
    """Parse T5 output into a dict with at least function/expression and range."""
    text = (raw_output or "").strip()
    if not text:
        return None

    text = re.sub(r"^\s*json\s*:\s*", "", text, flags=re.IGNORECASE)

    candidates: List[str] = [text]
    extracted = _extract_json(text)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        normalized = candidate
        if not normalized.startswith("{"):
            normalized = "{" + normalized + "}"
        normalized = re.sub(r"([,{]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', normalized)
        normalized = normalized.replace("'", '"')
        try:
            data = json.loads(normalized)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # Final regex fallback for simple key:value strings.
    function_match = re.search(r"(?:function|expression)\s*[:=]\s*([^,]+)", text, re.IGNORECASE)
    range_match = re.search(r"(?:range|x_range)\s*[:=]\s*\[([^\]]+)\]", text, re.IGNORECASE)
    parsed: Dict[str, Any] = {}

    if function_match:
        parsed["function"] = function_match.group(1).strip()
    else:
        equation_match = re.search(
            r"(?:y|f\(x\))\s*=\s*(.+?)(?:\s+(?:from|for)\s+|$)",
            text,
            re.IGNORECASE,
        )
        if equation_match:
            parsed["function"] = equation_match.group(1).strip()

    if range_match:
        parsed["range"] = [p.strip() for p in range_match.group(1).split(",") if p.strip()]
    else:
        natural_range = re.search(
            r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:[\.;,]|$)",
            text,
            re.IGNORECASE,
        )
        if natural_range:
            parsed["range"] = [natural_range.group(1).strip(), natural_range.group(2).strip()]

    return parsed if parsed.get("function") else None


def _build_plot_plan_from_structured(
    user_prompt: str, data: Dict[str, Any]
) -> Optional[AnimationPlan]:
    """Map structured graph JSON into a deterministic draw_curve animation plan."""
    raw_expr = data.get("function") or data.get("expression")
    expression = _sanitize_plot_expression(raw_expr)
    if not expression:
        return None

    raw_range: Any = data.get("range", data.get("x_range"))
    if raw_range is None or raw_range == "" or raw_range == []:
        natural_range = re.search(
            r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:[\.;,]|$)",
            user_prompt,
            re.IGNORECASE,
        )
        if natural_range:
            raw_range = [natural_range.group(1).strip(), natural_range.group(2).strip()]

    x_range = _coerce_range(raw_range, _PLOT_DEFAULT_X_RANGE)
    y_range = _coerce_range(data.get("y_range"), _PLOT_DEFAULT_Y_RANGE)
    title = str(data.get("title") or f"Function Plot: {user_prompt[:36]}").strip()[:80]
    color = _canonical_plot_color(data.get("color"))

    curve_params = {
        "expression": expression,
        "x_range": x_range,
        "y_range": y_range,
        "color": color,
    }

    return AnimationPlan(
        title=title,
        style="3b1b",
        template="draw_curve",
        parameters=curve_params,
        scenes=[
            AnimationScene(
                scene_id="curve_plot",
                template="draw_curve",
                parameters=curve_params,
                narration="Plot the requested function on the specified range.",
            )
        ],
    )


def _attempt_t5_structured_plan(user_prompt: str) -> tuple[Optional[AnimationPlan], Dict[str, Any]]:
    """Try to build a direct structured plan from T5 output."""
    meta: Dict[str, Any] = {
        "enabled": T5_STRUCTURED_ENABLED,
        "executed": False,
        "used": False,
        "model": T5_MODEL_NAME,
    }

    cleaned_prompt = re.sub(r"\s+", " ", (user_prompt or "").strip())
    if not cleaned_prompt:
        meta["reason"] = "empty_prompt"
        return None, meta

    if not T5_STRUCTURED_ENABLED:
        meta["reason"] = "disabled"
        return None, meta

    try:
        tokenizer, model = _load_t5_preprocessor()
        inputs = tokenizer(
            f"{T5_STRUCTURED_TASK_PREFIX}{cleaned_prompt}",
            return_tensors="pt",
            truncation=True,
            max_length=T5_MAX_INPUT_TOKENS,
        )

        generate_kwargs = {
            "max_new_tokens": T5_STRUCTURED_MAX_NEW_TOKENS,
            "num_beams": 4,
            "do_sample": False,
            "early_stopping": True,
            "no_repeat_ngram_size": 3,
        }

        if torch is not None:
            with torch.no_grad():
                output_ids = model.generate(**inputs, **generate_kwargs)
        else:
            output_ids = model.generate(**inputs, **generate_kwargs)

        meta["executed"] = True
        decoded = tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        meta["raw_output"] = decoded[:240]

        structured_data = _parse_t5_structured_output(decoded)
        if not structured_data:
            meta["reason"] = "parse_failed"
            return None, meta

        plan = _build_plot_plan_from_structured(cleaned_prompt, structured_data)
        if not plan:
            meta["reason"] = "unsupported_structured_output"
            return None, meta

        meta["used"] = True
        meta["reason"] = "ok"
        return plan, meta
    except Exception as e:
        meta["reason"] = f"structured_t5_failed: {e}"
        logger.warning("T5 structured plan stage failed: %s", e)
        return None, meta


def _attach_input_understanding_metadata(
    plan: AnimationPlan, t5_meta: Dict[str, Any], structured_meta: Dict[str, Any]
) -> AnimationPlan:
    """Attach debugging metadata for T5 normalization + structured stage."""
    plan_copy = plan.model_copy(deep=True)
    params = dict(plan_copy.parameters or {})

    enhanced_prompt = {
        "executed": bool(t5_meta.get("executed")),
        "applied": bool(t5_meta.get("applied")),
        "reason": t5_meta.get("reason", "ok"),
        "text": t5_meta.get("text", ""),
    }

    metadata = {
        "preprocessor": "t5",
        "required": True,
        "mode": t5_meta.get("mode", "enhance_preserve"),
        "model": t5_meta.get("model"),
        "source_prompt_preview": t5_meta.get("source_prompt", ""),
        "enhanced_prompt": enhanced_prompt,
        # Backward-compatible alias for clients that still expect this key.
        "normalized_prompt": dict(enhanced_prompt),
        "structured_stage": {
            "enabled": bool(structured_meta.get("enabled")),
            "executed": bool(structured_meta.get("executed")),
            "used": bool(structured_meta.get("used")),
            "reason": structured_meta.get("reason", "unknown"),
        },
    }

    planning_preview = t5_meta.get("planning_prompt_preview")
    if planning_preview:
        metadata["planning_prompt_preview"] = planning_preview

    raw_preview = structured_meta.get("raw_output")
    if raw_preview:
        metadata["structured_stage"]["raw_output_preview"] = raw_preview

    params["input_understanding"] = metadata
    plan_copy.parameters = params
    return plan_copy


def _sanitize_identifier(raw: Any, default_prefix: str) -> str:
    ident = re.sub(r"[^0-9a-zA-Z_]", "_", str(raw or "").strip())
    ident = re.sub(r"_+", "_", ident).strip("_")
    if not ident:
        ident = default_prefix
    if ident[0].isdigit():
        ident = f"{default_prefix}_{ident}"
    return ident


def _ensure_unique_identifier(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    i = 2
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"


def _canonical_object_type(raw_type: Any) -> str:
    t = str(raw_type or "text").strip().lower().replace("-", "_").replace(" ", "_")
    t = _OBJECT_TYPE_ALIASES.get(t, t)
    return t if t in _SAFE_GENERIC_OBJECT_TYPES else "text"


def _canonical_action(raw_action: Any) -> str:
    a = str(raw_action or "fade_in").strip().lower().replace("-", "_").replace(" ", "_")
    a = _ACTION_ALIASES.get(a, a)
    return a if a in _SAFE_GENERIC_ACTIONS else "fade_in"


def _extract_key_terms(prompt: str, max_terms: int = 4) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", prompt.lower())
    stop = {
        "what",
        "how",
        "why",
        "when",
        "where",
        "which",
        "does",
        "with",
        "from",
        "that",
        "this",
        "these",
        "those",
        "about",
        "into",
        "your",
        "their",
        "have",
        "will",
        "would",
        "could",
        "should",
        "through",
        "using",
        "explain",
    }
    terms: List[str] = []
    for t in tokens:
        if t in stop:
            continue
        if t not in terms:
            terms.append(t)
        if len(terms) >= max_terms:
            break
    return terms


def _build_render_profile(user_prompt: str) -> Dict[str, Any]:
    """Derive global rendering profile from prompt quality cues."""
    p = (user_prompt or "").lower()

    wants_advanced = any(h in p for h in _ADVANCED_RENDER_HINTS)
    wants_more_frames = any(h in p for h in _HIGH_FRAME_HINTS)
    wants_concise = any(h in p for h in _CONCISE_RENDER_HINTS)

    if wants_concise and not wants_advanced:
        profile = {
            "detail_level": "concise",
            "animation_density": "medium",
            "pace_scale": 0.9,
            "scene_min_duration": 3.2,
            "inter_scene_wait": 0.7,
            "transition_fade_duration": 0.5,
            "inter_action_wait": 0.0,
            "scene_pause": 0.8,
            "target_min_scenes": 3,
            "quality": "medium",
            "frame_rate": 30,
        }
    elif wants_advanced:
        profile = {
            "detail_level": "advanced",
            "animation_density": "high",
            "pace_scale": 1.35,
            "scene_min_duration": 6.0,
            "inter_scene_wait": 1.2,
            "transition_fade_duration": 0.9,
            "inter_action_wait": 0.08,
            "scene_pause": 1.4,
            "target_min_scenes": 5,
            "quality": "high",
            "frame_rate": 60 if wants_more_frames else 48,
        }
    else:
        profile = {
            "detail_level": "standard",
            "animation_density": "medium",
            "pace_scale": 1.05,
            "scene_min_duration": 4.2,
            "inter_scene_wait": 0.9,
            "transition_fade_duration": 0.7,
            "inter_action_wait": 0.0,
            "scene_pause": 1.0,
            "target_min_scenes": 4,
            "quality": "medium",
            "frame_rate": 36 if wants_more_frames else 30,
        }

    return profile


def _enrich_generic_scene_for_density(scene: AnimationScene, max_objects: int = 3) -> None:
    """Add non-destructive emphasis steps so generic scenes feel richer."""
    if scene.template not in {None, "generic"}:
        return

    obj_ids = [o.id for o in scene.objects if o.id]
    if not obj_ids:
        return

    existing_pairs = {(a.object_id, a.action) for a in scene.animations}
    active_ids = {a.object_id for a in scene.animations}

    for oid in obj_ids[:max_objects]:
        if oid not in active_ids:
            scene.animations.append(AnimationStep(object_id=oid, action="fade_in", duration=0.9))

    for oid in obj_ids[:max_objects]:
        if (oid, "indicate") not in existing_pairs:
            scene.animations.append(AnimationStep(object_id=oid, action="indicate", duration=0.8))

    if len(obj_ids) >= 2 and not any(a.action == "connect" for a in scene.animations):
        scene.animations.append(
            AnimationStep(
                object_id=obj_ids[0],
                action="connect",
                parameters={"target": obj_ids[1]},
                duration=1.0,
            )
        )


def _apply_render_profile_to_plan(
    plan: AnimationPlan, profile: Dict[str, Any], user_prompt: str
) -> AnimationPlan:
    """Inject global render profile and increase scene richness in hybrid mode."""
    plan_copy = plan.model_copy(deep=True)

    params = dict(plan_copy.parameters or {})
    params["render_profile"] = profile
    params.setdefault("frame_rate", profile.get("frame_rate", 30))
    params.setdefault("inter_scene_wait", profile.get("inter_scene_wait", 1.0))
    params.setdefault("transition_fade_duration", profile.get("transition_fade_duration", 0.8))
    params.setdefault("style", plan_copy.style or "3b1b")
    plan_copy.parameters = params

    if profile.get("quality") == "high":
        plan_copy.quality = "high"

    if not plan_copy.scenes:
        return plan_copy

    pace_scale = float(profile.get("pace_scale", 1.0))
    pace_scale = max(0.8, min(2.0, pace_scale))
    is_advanced = profile.get("detail_level") == "advanced"
    target_min_scenes = int(profile.get("target_min_scenes", 4))

    # Add deep-dive scene(s) when user requests richer/complex outputs.
    key_terms = _extract_key_terms(user_prompt, max_terms=5)
    existing_scene_ids = {s.scene_id for s in plan_copy.scenes}
    while is_advanced and len(plan_copy.scenes) < min(target_min_scenes, 6):
        scene_id = _ensure_unique_identifier("deep_dive", existing_scene_ids)
        existing_scene_ids.add(scene_id)
        depends = [plan_copy.scenes[-1].scene_id] if plan_copy.scenes else []
        emphasis = " -> ".join(t.title() for t in key_terms) if key_terms else "Core Mechanism"
        deep_scene = AnimationScene(
            scene_id=scene_id,
            template="generic",
            depends_on=depends,
            objects=[
                AnimationObject(
                    id="deep_title",
                    type="text",
                    parameters={"text": "Deep Dive", "position": [0, 2.3, 0], "font_size": 36},
                ),
                AnimationObject(
                    id="deep_points",
                    type="text",
                    parameters={"text": emphasis, "position": [0, 0.8, 0], "font_size": 28},
                ),
            ],
            animations=[
                AnimationStep(object_id="deep_title", action="write", duration=1.2),
                AnimationStep(object_id="deep_points", action="fade_in", duration=1.0),
                AnimationStep(object_id="deep_points", action="highlight", duration=0.9),
            ],
            narration="Let's examine the mechanics in more depth before concluding.",
        )
        plan_copy.scenes.append(deep_scene)

    for scene in plan_copy.scenes:
        scene_params = dict(scene.parameters or {})
        scene_params.setdefault("render_profile", profile)
        scene.parameters = scene_params

        if profile.get("animation_density") == "high":
            _enrich_generic_scene_for_density(scene)

        for step in scene.animations:
            base_duration = step.duration if step.duration > 0 else step.estimate_duration()
            step.duration = round(max(0.2, base_duration * pace_scale), 2)

        if scene.duration > 0:
            scene.duration = round(max(scene.duration * pace_scale, 2.5), 2)

    return plan_copy


def _finalize_plan_durations(plan: AnimationPlan, profile: Dict[str, Any]) -> AnimationPlan:
    """Finalize explicit scene and total durations for scheduling/metadata."""
    plan_copy = plan.model_copy(deep=True)
    min_scene_duration = float(profile.get("scene_min_duration", 4.0))
    inter_scene_wait = float(profile.get("inter_scene_wait", 1.0))

    if not plan_copy.scenes:
        return plan_copy

    total = 0.0
    for scene in plan_copy.scenes:
        effective = scene.duration if scene.duration > 0 else scene.get_effective_duration()
        effective = max(effective, min_scene_duration)
        scene.duration = round(effective, 2)
        total += scene.duration

    total += max(0, len(plan_copy.scenes) - 1) * max(0.0, inter_scene_wait)
    plan_copy.duration = round(total, 2)
    return plan_copy


def _build_template_free_plan(user_prompt: str, style: Optional[str], title: str) -> AnimationPlan:
    prompt_line = re.sub(r"\s+", " ", (user_prompt or "New concept").strip())[:96]
    title_line = re.sub(r"\s+", " ", (title or prompt_line or "Concept Overview").strip())[:64]
    key_terms = _extract_key_terms(user_prompt)
    key_line = ", ".join(t.title() for t in key_terms) if key_terms else "Core ideas"

    return AnimationPlan(
        title=title_line,
        style=style or "3b1b",
        template=None,
        scenes=[
            AnimationScene(
                scene_id="intro",
                template="generic",
                objects=[
                    AnimationObject(
                        id="title",
                        type="text",
                        parameters={"text": title_line, "position": [0, 2.6, 0], "font_size": 40},
                    ),
                    AnimationObject(
                        id="question",
                        type="text",
                        parameters={"text": prompt_line, "position": [0, 0.9, 0], "font_size": 28},
                    ),
                ],
                animations=[
                    AnimationStep(object_id="title", action="write", duration=1.5),
                    AnimationStep(object_id="question", action="fade_in", duration=1.0),
                ],
                narration=f"We will break down this concept: {prompt_line}",
            ),
            AnimationScene(
                scene_id="core_ideas",
                template="generic",
                depends_on=["intro"],
                objects=[
                    AnimationObject(
                        id="core",
                        type="text",
                        parameters={"text": "Key ideas", "position": [0, 2.4, 0], "font_size": 34},
                    ),
                    AnimationObject(
                        id="ideas",
                        type="text",
                        parameters={"text": key_line, "position": [0, 0.7, 0], "font_size": 30},
                    ),
                ],
                animations=[
                    AnimationStep(object_id="core", action="write", duration=1.2),
                    AnimationStep(object_id="ideas", action="fade_in", duration=1.0),
                    AnimationStep(object_id="ideas", action="highlight", duration=1.0),
                ],
                narration="Here are the central ideas we need to understand.",
            ),
            AnimationScene(
                scene_id="summary",
                template="generic",
                depends_on=["core_ideas"],
                objects=[
                    AnimationObject(
                        id="summary_title",
                        type="text",
                        parameters={"text": "Takeaway", "position": [0, 2.2, 0], "font_size": 34},
                    ),
                    AnimationObject(
                        id="summary_text",
                        type="text",
                        parameters={
                            "text": f"{title_line} in simple steps",
                            "position": [0, 0.6, 0],
                            "font_size": 30,
                        },
                    ),
                ],
                animations=[
                    AnimationStep(object_id="summary_title", action="write", duration=1.0),
                    AnimationStep(object_id="summary_text", action="fade_in", duration=1.0),
                ],
                narration="Now you have a clean mental model of how this concept works.",
            ),
        ],
    )


def _sanitize_scene_for_generic(
    scene: AnimationScene, scene_idx: int, user_prompt: str
) -> AnimationScene:
    raw_scene_id = scene.scene_id or f"scene_{scene_idx + 1}"
    safe_scene_id = _sanitize_identifier(raw_scene_id, f"scene_{scene_idx + 1}")

    id_map: Dict[str, str] = {}
    existing_ids: set[str] = set()
    safe_objects: List[AnimationObject] = []

    for obj_idx, obj in enumerate(scene.objects or []):
        raw_obj_id = obj.id or f"obj_{obj_idx + 1}"
        base_obj_id = _sanitize_identifier(raw_obj_id, f"obj_{obj_idx + 1}")
        safe_obj_id = _ensure_unique_identifier(base_obj_id, existing_ids)
        existing_ids.add(safe_obj_id)

        id_map[str(raw_obj_id)] = safe_obj_id
        id_map[safe_obj_id] = safe_obj_id

        obj_type = _canonical_object_type(obj.type)
        params = dict(obj.parameters or {})
        if obj_type in {"text", "label"} and not params.get("text") and not params.get("label"):
            params["text"] = str(raw_obj_id).replace("_", " ").title()

        safe_objects.append(AnimationObject(id=safe_obj_id, type=obj_type, parameters=params))

    safe_animations: List[AnimationStep] = []
    for anim_idx, anim in enumerate(scene.animations or []):
        raw_ref = str(anim.object_id or f"auto_obj_{anim_idx + 1}")
        safe_ref = id_map.get(raw_ref)
        if not safe_ref:
            safe_ref = _ensure_unique_identifier(
                _sanitize_identifier(raw_ref, f"auto_obj_{anim_idx + 1}"), existing_ids
            )
            existing_ids.add(safe_ref)
            id_map[raw_ref] = safe_ref
            safe_objects.append(
                AnimationObject(
                    id=safe_ref,
                    type="text",
                    parameters={"text": safe_ref.replace("_", " ").title()},
                )
            )

        action = _canonical_action(anim.action)
        params = dict(anim.parameters or {})

        if action in {"transform", "connect"}:
            raw_target = params.get("target")
            if raw_target:
                safe_target = id_map.get(str(raw_target))
                if not safe_target:
                    safe_target = _ensure_unique_identifier(
                        _sanitize_identifier(raw_target, f"target_{anim_idx + 1}"), existing_ids
                    )
                    existing_ids.add(safe_target)
                    id_map[str(raw_target)] = safe_target
                    safe_objects.append(
                        AnimationObject(
                            id=safe_target,
                            type="text",
                            parameters={"text": safe_target.replace("_", " ").title()},
                        )
                    )
            else:
                safe_target = _ensure_unique_identifier(f"{safe_ref}_target", existing_ids)
                existing_ids.add(safe_target)
                safe_objects.append(
                    AnimationObject(
                        id=safe_target,
                        type="text",
                        parameters={"text": safe_target.replace("_", " ").title()},
                    )
                )
            params["target"] = safe_target

        safe_animations.append(
            AnimationStep(
                object_id=safe_ref,
                action=action,
                parameters=params,
                duration=anim.duration,
            )
        )

    if not safe_objects:
        safe_objects = [
            AnimationObject(
                id="topic",
                type="text",
                parameters={"text": (scene.description or user_prompt or "Concept")[:80]},
            )
        ]
        existing_ids.add("topic")

    if not safe_animations:
        safe_animations = [
            AnimationStep(object_id=safe_objects[0].id, action="write", duration=1.5)
        ]

    return AnimationScene(
        scene_id=safe_scene_id,
        description=scene.description,
        template="generic",
        templates=[],
        depends_on=list(scene.depends_on or []),
        parameters={},
        objects=safe_objects,
        animations=safe_animations,
        narration=scene.narration or (scene.description or f"Explaining {user_prompt[:72]}"),
        duration=scene.duration,
        output_objects=[o.id for o in safe_objects],
    )


def _stabilize_plan_for_rendering(
    plan: AnimationPlan, user_prompt: str, intent: Optional[UserIntent]
) -> AnimationPlan:
    """Normalize plan so unseen/complex prompts render safely with generic primitives."""
    plan_copy = plan.model_copy(deep=True)

    # Unknown top-level templates are unsafe. Route through generic-safe rendering.
    if (
        plan_copy.template
        and plan_copy.template not in AVAILABLE_TEMPLATES
        and plan_copy.template != "generic"
    ):
        plan_copy.template = "generic"

    use_template_free_mode = intent is None

    if use_template_free_mode and not plan_copy.scenes:
        return _build_template_free_plan(user_prompt, plan_copy.style, plan_copy.title)

    if not plan_copy.scenes and plan_copy.template in {None, "generic"}:
        return _build_template_free_plan(user_prompt, plan_copy.style, plan_copy.title)

    scene_id_map: Dict[str, str] = {}
    sanitized_scenes: List[AnimationScene] = []

    for idx, scene in enumerate(plan_copy.scenes or []):
        should_force_generic = (
            use_template_free_mode
            or scene.template in {None, "generic"}
            or scene.template not in AVAILABLE_TEMPLATES
            or any(t not in AVAILABLE_TEMPLATES for t in (scene.templates or []))
        )

        if should_force_generic:
            sanitized = _sanitize_scene_for_generic(scene, idx, user_prompt)
        else:
            # Keep known template scenes mostly intact, but sanitize scene id for safety.
            sanitized = scene.model_copy(deep=True)
            sanitized.scene_id = _sanitize_identifier(sanitized.scene_id, f"scene_{idx + 1}")

        scene_id_map[str(scene.scene_id)] = sanitized.scene_id
        sanitized_scenes.append(sanitized)

    all_scene_ids = {s.scene_id for s in sanitized_scenes}
    for s in sanitized_scenes:
        mapped_depends: List[str] = []
        for dep in s.depends_on:
            mapped = scene_id_map.get(str(dep), _sanitize_identifier(dep, "scene"))
            if mapped in all_scene_ids and mapped != s.scene_id and mapped not in mapped_depends:
                mapped_depends.append(mapped)
        s.depends_on = mapped_depends

    plan_copy.scenes = sanitized_scenes
    if use_template_free_mode:
        plan_copy.template = None

    return plan_copy


def refine_plan(
    original_prompt: str, original_plan: AnimationPlan, refinement_prompt: str
) -> AnimationPlan:
    """Refine an existing animation plan based on user feedback."""
    refine_context = f"""
ORIGINAL PROMPT: {original_prompt}
ORIGINAL PLAN: {original_plan.model_dump_json()}
REFINEMENT REQUEST: {refinement_prompt}

Please update the plan according to the REFINEMENT REQUEST.
"""
    # Use the same LLM logic but with refinement context
    try:
        # In a real scenario, you'd call the LLM here with the refinement context.
        # For now, we'll simulate it by calling the same logic but with the combined prompt.
        plan = call_combined_llm_planner(refine_context)
        return plan
    except Exception as e:
        logger.error(f"Refinement failed: {e}")
        return original_plan


def generate_plan(user_prompt: str) -> AnimationPlan:
    """
    Generate animation plan with combined intent extraction, caching, and validation.
    """
    enhanced_prompt, t5_meta = _normalize_prompt_with_t5(user_prompt)
    prompt_for_planning = _merge_prompt_with_enhancement(user_prompt, enhanced_prompt)
    t5_meta["planning_prompt_preview"] = prompt_for_planning[:280]

    if t5_meta.get("applied"):
        logger.info("T5 enhanced prompt for planning")

    prompt_for_profile = user_prompt or enhanced_prompt or prompt_for_planning
    render_profile = _build_render_profile(prompt_for_profile)
    structured_seed_prompt = user_prompt or enhanced_prompt or prompt_for_planning
    structured_plan, t5_struct_meta = _attempt_t5_structured_plan(structured_seed_prompt)

    if structured_plan is not None:
        plan = _apply_render_profile_to_plan(structured_plan, render_profile, prompt_for_profile)
        plan = _attach_input_understanding_metadata(plan, t5_meta, t5_struct_meta)
        plan = _finalize_plan_durations(plan, render_profile)
        logger.info("Using direct T5 structured plan path")
        return plan

    def _profiled_fallback_plan(prompt_text: str) -> AnimationPlan:
        fallback_prompt = prompt_text or prompt_for_profile
        fallback_title = (fallback_prompt or "Concept Overview")[:60]
        fallback = _build_template_free_plan(fallback_prompt, "3b1b", fallback_title)
        fallback = _apply_render_profile_to_plan(fallback, render_profile, fallback_prompt)
        fallback = _attach_input_understanding_metadata(fallback, t5_meta, t5_struct_meta)
        return _finalize_plan_durations(fallback, render_profile)

    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set, using fallback plan")
            return _profiled_fallback_plan(prompt_for_profile)
    elif LLM_PROVIDER == "openai":
        if not (OPENAI_API_KEY or OPENAI_BASE_URL):
            logger.warning("OPENAI configuration missing, using fallback plan")
            return _profiled_fallback_plan(prompt_for_profile)
    else:
        logger.warning(f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}', using fallback plan")
        return _profiled_fallback_plan(prompt_for_profile)

    # 1. Check Redis Cache
    cache_key = f"plan_v3:{hashlib.md5(prompt_for_planning.encode()).hexdigest()}"
    try:
        cached_plan = redis_client.get(cache_key)
        if cached_plan:
            logger.info("Plan found in cache", extra={"prompt": prompt_for_planning[:50]})
            return AnimationPlan.model_validate_json(cached_plan)
    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")

    # 2. Concept Router (Lightweight check before LLM)
    concept_intent = rule_based_concept_router(prompt_for_profile)

    # guard against enormous prompts
    if len(prompt_for_planning) > 2000:
        logger.warning("Prompt too long; truncating to 2000 chars")
        prompt_for_planning = prompt_for_planning[:2000]

    try:
        plan = call_combined_llm_planner(prompt_for_planning, concept_intent)

        # Force template if detected by router but not set by LLM
        if concept_intent and concept_intent.template and not plan.template:
            plan.template = concept_intent.template

        # Strong override for MNIST prompts to avoid generic neural-network-only output.
        if (
            concept_intent
            and concept_intent.concept == "mnist"
            and plan.template
            in {
                None,
                "generic",
                "neural_network",
            }
        ):
            plan.template = "mnist_recognition"

        # Strong override for BFS-vs-DFS prompts to ensure side-by-side comparison output.
        if concept_intent and concept_intent.concept == "bfs_dfs_comparison":
            plan.template = "bfs_dfs_comparison"

        # Strong override for ChatGPT/LLM architecture prompts.
        if (
            concept_intent
            and concept_intent.concept in {"llm_pipeline", "tokenization"}
            and plan.template in {None, "generic"}
        ):
            plan.template = "transformer_attention"

        # Self-attention prompts should always get sentence-level parameters.
        if concept_intent and concept_intent.concept == "self_attention":
            if plan.template in {None, "generic"}:
                plan.template = "transformer_attention"
            plan_params = dict(plan.parameters or {})
            plan_params.setdefault("sentence", "The cat chased the mouse because it was hungry.")
            plan_params.setdefault("focus_token", "it")
            plan.parameters = plan_params

        # 4. Validate Plan
        violations = validate_plan_against_intent(plan, concept_intent, prompt_for_profile)
        if violations:
            logger.warning(f"Plan violations detected: {violations}")
            plan = repair_plan(prompt_for_profile, concept_intent, plan, violations)

        # 4.5 Stabilize for unseen/complex prompts and sanitize unsafe scene references.
        plan = _stabilize_plan_for_rendering(plan, prompt_for_profile, concept_intent)

        # 4.6 Apply prompt-aware hybrid render profile for richer pacing and density.
        plan = _apply_render_profile_to_plan(plan, render_profile, prompt_for_profile)

        # Attach lightweight debugging metadata for input understanding.
        plan = _attach_input_understanding_metadata(plan, t5_meta, t5_struct_meta)

        # 5. Post-process narration and durations in plan (Phase 3)
        try:
            pipeline = NarrationPipeline()
            plan = pipeline.process_plan(plan)
        except Exception as ex:
            logger.warning(f"Narration pipeline post-processing failed: {ex}")

        # 5.5 Finalize explicit durations after narration sync.
        plan = _finalize_plan_durations(plan, render_profile)

        # 6. Cache result
        try:
            redis_client.setex(cache_key, 3600 * 24, plan.model_dump_json())
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")

        logger.info(
            "plan_generated",
            extra={
                "template": plan.template,
                "title": plan.title,
                "scenes": len(plan.scenes) if plan.scenes else 1,
            },
        )
        return plan

    except LLMQuotaExceededError as e:
        logger.error(f"LLM quota exceeded: {e}")
        # return a minimal fallback that instructs the user to simplify
        fallback = AnimationPlan.create_rate_limited_fallback(prompt_for_profile)
        fallback = _apply_render_profile_to_plan(fallback, render_profile, prompt_for_profile)
        fallback = _attach_input_understanding_metadata(fallback, t5_meta, t5_struct_meta)
        return _finalize_plan_durations(fallback, render_profile)
    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        fallback = AnimationPlan.create_fallback(prompt_for_profile)
        fallback = _apply_render_profile_to_plan(fallback, render_profile, prompt_for_profile)
        fallback = _attach_input_understanding_metadata(fallback, t5_meta, t5_struct_meta)
        return _finalize_plan_durations(fallback, render_profile)


def generate_manim_code(user_prompt: str) -> str:
    """
    Generate Manim Python code from user prompt.
    """
    # 1. Generate the plan (uses caching, combined LLM call, and validation)
    plan = generate_plan(user_prompt)

    # 2. Convert plan to code using the template engine directly.
    from app.templates.engine import render_multi_scene_plan, render_template

    if plan.template and plan.template != "generic":
        return render_template(plan.template, plan.parameters or {})

    if plan.scenes:
        return render_multi_scene_plan(plan.model_dump())

    return render_template("generic", plan.model_dump())


def rule_based_concept_router(prompt: str) -> Optional[UserIntent]:
    """
    Lightweight concept detection for routing to appropriate Phase 1/2 templates.
    Returns a hint for the LLM planner.
    """
    p = prompt.lower()

    # LLM / NLP concepts
    if ("chatgpt" in p or "gpt" in p or "llm" in p or "large language model" in p) and (
        "how" in p or "work" in p or "works" in p or "architecture" in p
    ):
        return UserIntent(concept="llm_pipeline", template="transformer_attention")
    if "tokenization" in p or ("token" in p and ("gpt" in p or "chatgpt" in p or "llm" in p)):
        return UserIntent(concept="tokenization", template="transformer_attention")
    if "markov" in p:
        return UserIntent(concept="markov_chain", template="graph_visualization")
    if "mnist" in p or (
        ("recognize" in p or "classification" in p) and ("digit" in p or "handwritten" in p)
    ):
        return UserIntent(concept="mnist", template="mnist_recognition")
    if "cramer" in p or ("system" in p and "linear equation" in p):
        return UserIntent(concept="cramers_rule", template="generic")

    # Linear Algebra concepts
    if "eigenvector" in p or "eigenvalue" in p:
        return UserIntent(concept="eigenvectors", template="eigenvector")
    if "projection" in p and "vector" in p:
        return UserIntent(concept="vector_projection", template="vector_transformation")
    if "basis" in p and ("change" in p or "transform" in p):
        return UserIntent(concept="basis_change", template="basis_change")
    if "dot product" in p or "dot product" in p:
        return UserIntent(concept="dot_product", template="dot_product")

    # Calculus concepts
    if ("derivative" in p or "tangent" in p) and "slope" in p:
        return UserIntent(concept="derivative_slope", template="derivative_slope")
    if "integral" in p and ("accumul" in p or "area" in p):
        return UserIntent(concept="integral_accumulation", template="integral_accumulation")
    if "chain rule" in p:
        return UserIntent(concept="chain_rule", template="chain_rule")
    if "gradient descent" in p:
        return UserIntent(concept="gradient_descent", template="gradient_descent_advanced")
    if "derivative" in p or "tangent" in p:
        return UserIntent(concept="derivative_tangent", template="derivative_tangent")

    # Algorithm concepts
    bfs_like = "bfs" in p or "breadth first" in p or "breadth-first" in p
    dfs_like = "dfs" in p or "depth first" in p or "depth-first" in p
    if bfs_like and dfs_like:
        return UserIntent(concept="bfs_dfs_comparison", template="bfs_dfs_comparison")

    if "bfs" in p or "breadth first" in p or "breadth-first" in p:
        return UserIntent(concept="bfs", template="bfs_traversal")
    if "dfs" in p or "depth first" in p or "depth-first" in p:
        return UserIntent(concept="dfs", template="dfs_traversal")
    if "dijkstra" in p or "shortest path" in p:
        return UserIntent(concept="dijkstra", template="dijkstra")
    if "topological" in p or "dag" in p or "task" in p and "order" in p:
        return UserIntent(concept="topological_sort", template="topological_sort")
    if "graph" in p and ("traverse" in p or "search" in p or "visit" in p):
        return UserIntent(concept="graph_search", template="graph_visualization")

    # Machine Learning concepts
    if "backpropagation" in p or "backprop" in p or ("back" in p and "gradient" in p):
        return UserIntent(concept="backpropagation", template="backpropagation")
    if "embedding" in p or "latent space" in p or "word vector" in p:
        return UserIntent(concept="embeddings", template="embedding_space")
    if "self-attention" in p or "self attention" in p:
        return UserIntent(concept="self_attention", template="transformer_attention")
    if "convolution" in p or ("filter" in p and "cnn" in p):
        return UserIntent(concept="convolution", template="convolution_filters")
    if "neural" in p or "network" in p:
        return UserIntent(concept="neural_network", template="neural_network")
    if "attention" in p or "transformer" in p:
        return UserIntent(concept="transformer", template="transformer_attention")

    # Phase 1 templates (backward compatibility)
    if "matr" in p and ("multiply" in p or "multiplicat" in p):
        return UserIntent(concept="matrix_multiplication", template="matrix_multiplication")
    if "projectile" in p or ("physics" in p and "ball" in p):
        return UserIntent(concept="projectile_motion", template="generic")
    if "vector" in p and ("transform" in p or "linear" in p):
        return UserIntent(concept="vector_transformation", template="vector_transformation")
    if "deriv" in p or "calculus" in p or "tangent" in p:
        return UserIntent(concept="calculus_derivative", template="derivative_slope")
    if "integral" in p or "area under" in p:
        return UserIntent(concept="calculus_integral", template="integral_accumulation")
    if "factor" in p or "polynomial" in p:
        return UserIntent(concept="algebra_factoring", template="generic")
    if "unit circle" in p or "trig" in p or "sin" in p or "cos" in p:
        return UserIntent(concept="trigonometry", template="unit_circle")
    if "sort" in p or "bubble" in p:
        return UserIntent(concept="sorting", template="sorting")
    if "dijkstra" in p or "shortest path" in p:
        return UserIntent(concept="dijkstra", template="dijkstra")

    # Fallback to capability-driven matching if no explicit rule matched
    registry = get_capability_registry()
    tokens = re.findall(r"\w+", p)
    for token in tokens:
        candidates = registry.find_templates_for_concept(token, composition_mode=True)
        if candidates:
            return UserIntent(concept=token, template=candidates[0])

    return None


def call_combined_llm_planner(user_prompt: str, hint: Optional[UserIntent] = None) -> AnimationPlan:
    """Single LLM call for both Intent and Plan with Phase 2 templates.

    Adds explicit brevity instructions and catches quota errors so callers
    can react appropriately (e.g. return a user-facing message).
    """
    full_prompt = COMBINED_PLANNER_PROMPT.format(user_prompt=user_prompt)
    full_prompt += (
        "\n\nNOTE: Produce 4 to 8 scenes with concrete visual actions and strong "
        "pedagogical depth. Keep the total plan under 2500 tokens while preserving "
        "critical technical detail from the user request."
    )
    if hint:
        full_prompt += (
            f"\n\nHINT: The user might be asking about '{hint.concept}'. "
            f"Consider using the '{hint.template}' template.\n"
        )
    if LLM_PROVIDER == "openai":
        try:
            try:
                from openai import OpenAI
            except Exception as ie:
                raise RuntimeError(f"OpenAI client unavailable: {ie}")
            kwargs: Dict[str, Any] = {}
            # Ensure api_key is always provided, even as a placeholder for local LLMs
            kwargs["api_key"] = OPENAI_API_KEY or "sk-placeholder"
            if OPENAI_BASE_URL:
                kwargs["base_url"] = OPENAI_BASE_URL
            client = OpenAI(**kwargs)
            messages = [
                {"role": "system", "content": "Return STRICT JSON only as specified."},
                {"role": "user", "content": full_prompt},
            ]
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=LLM_TEMPERATURE,
                messages=messages,
                max_tokens=1500,
            )
            content = resp.choices[0].message.content or ""
        except Exception as e:
            msg = str(e)
            if "rate limit" in msg.lower() or "quota" in msg.lower() or "429" in msg:
                raise LLMQuotaExceededError(msg)
            logger.error(f"OpenAI planner call failed: {e}")
            raise
        if not content:
            raise ValueError("Empty LLM response")
        data = json.loads(_extract_json(content))
        return AnimationPlan(**data["plan"])
    elif LLM_PROVIDER == "gemini":
        model = get_gemini_model()
        try:
            response = model.generate_content(full_prompt)
        except Exception as e:
            msg = str(e)
            if "quota" in msg.lower() or "limit" in msg.lower() or "429" in msg:
                raise LLMQuotaExceededError(msg)
            logger.error(f"Gemini planner call failed: {e}")
            raise
        if not response.text:
            raise ValueError("Empty LLM response")
        data = json.loads(_extract_json(response.text))
        return AnimationPlan(**data["plan"])
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'")


def validate_plan_against_intent(
    plan: AnimationPlan, intent: Optional[UserIntent], user_prompt: str
) -> list[str]:
    """
    Validator for the new Phase 2 DSL structure with composition support.
    """
    violations = []

    # Check primary template if specified
    if plan.template and plan.template not in AVAILABLE_TEMPLATES and plan.template != "generic":
        violations.append(f"Unknown template: {plan.template}")

    # Validate scenes — plan.scenes is the authoritative Pydantic list;
    # fall back to the legacy parameters dict for old-style plans.
    scenes = (
        [s.model_dump() for s in plan.scenes] if plan.scenes else plan.parameters.get("scenes", [])
    )
    if not scenes:
        violations.append("Plan must have at least one scene")

    if len(scenes) > 8:  # Allow up to 8 scenes for complex explanations
        violations.append(f"Too many scenes: max 8, got {len(scenes)}")

    # Validate each scene
    for scene in scenes:
        scene_id = scene.get("scene_id", "unknown")

        # Check composition mode
        templates = scene.get("templates", [])
        if templates:
            # Composition mode - validate each template
            for t_name in templates:
                if t_name not in AVAILABLE_TEMPLATES:
                    violations.append(f"Scene '{scene_id}' uses unknown template: {t_name}")
        else:
            # Single template mode
            t_name = scene.get("template", "generic")
            if t_name not in AVAILABLE_TEMPLATES and t_name != "generic":
                violations.append(f"Scene '{scene_id}' uses unknown template: {t_name}")

        # Check dependencies (must reference existing scenes)
        depends = scene.get("depends_on", [])
        scene_ids = {s.get("scene_id") for s in scenes}
        for dep in depends:
            if dep not in scene_ids:
                violations.append(f"Scene '{scene_id}' depends on non-existent scene: {dep}")

        # Check narration
        if not scene.get("narration"):
            violations.append(f"Scene '{scene_id}' missing narration for voice-over")

    return violations


def repair_plan(
    user_prompt: str, intent: Optional[UserIntent], plan: AnimationPlan, violations: list[str]
) -> AnimationPlan:
    """Repair loop using the correct DSL schema."""
    logger.info(f"Attempting plan repair for violations: {violations}")

    repair_prompt = f"""The generated animation plan is invalid. FIX IT.
USER REQUEST: {user_prompt}
CURRENT PLAN: {plan.model_dump_json()}
VIOLATIONS: {violations}

Return ONLY the corrected JSON following the combined output format (intent + plan).
"""
    try:
        if LLM_PROVIDER == "openai":
            try:
                from openai import OpenAI
            except Exception as ie:
                raise RuntimeError(f"OpenAI client unavailable: {ie}")
            kwargs: Dict[str, Any] = {}
            if OPENAI_API_KEY:
                kwargs["api_key"] = OPENAI_API_KEY
            if OPENAI_BASE_URL:
                kwargs["base_url"] = OPENAI_BASE_URL
            client = OpenAI(**kwargs)
            messages = [
                {"role": "system", "content": "Return STRICT JSON only as specified."},
                {"role": "user", "content": repair_prompt},
            ]
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=LLM_TEMPERATURE,
                messages=messages,
            )
            content = resp.choices[0].message.content or ""
            data = json.loads(_extract_json(content))
            return AnimationPlan(**data["plan"])
        else:
            model = get_gemini_model()
            response = model.generate_content(repair_prompt)
            data = json.loads(_extract_json(response.text))
            return AnimationPlan(**data["plan"])
    except Exception as e:
        logger.error(f"Repair failed: {e}")
        return plan


def get_gemini_model():
    """Configure and return Gemini model with safety settings."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    # Safety settings to reduce blocked outputs
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    return genai.GenerativeModel(
        model_name=LLM_MODEL,
        generation_config={
            "temperature": LLM_TEMPERATURE,
            "max_output_tokens": 4096,
        },
        safety_settings=safety_settings,
    )


def _extract_json(text: str) -> str:
    """
    Extract JSON from text, handling markdown code blocks and preamble.
    """
    text = text.strip()

    # 1. Try to find content between triple backticks
    if "```" in text:
        # Match ```json ... ``` or just ``` ... ```
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if m:
            return m.group(1).strip()

    # 2. Fallback: Find the first '{' and last '}'
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    # 3. Last resort: Return as-is
    return text
