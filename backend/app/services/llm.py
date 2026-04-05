"""LLM service for generating animation plans using Google Gemini with intent validation."""

import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional

try:
    import numpy as np
except Exception:
    np = None

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory

try:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
except Exception:
    torch = None
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None

from app.schemas.animation import AnimationObject, AnimationPlan, AnimationScene, AnimationStep
from app.schemas.intent import UserIntent
from app.services.narration import NarrationPipeline
from app.templates.capabilities import get_capability_registry
from app.templates.engine import TEMPLATES as AVAILABLE_TEMPLATES

logger = logging.getLogger(__name__)


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
T5_MAX_INPUT_TOKENS = int(os.getenv("T5_MAX_INPUT_TOKENS", "512"))
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
    "",
)
T5_STRUCTURED_MAX_NEW_TOKENS = int(os.getenv("T5_STRUCTURED_MAX_NEW_TOKENS", "96"))
T5_STRUCTURED_MAX_LENGTH = int(os.getenv("T5_STRUCTURED_MAX_LENGTH", "512"))
T5_STRUCTURED_TEMPERATURE = float(os.getenv("T5_STRUCTURED_TEMPERATURE", "0.2"))
T5_STRUCTURED_TOP_P = float(os.getenv("T5_STRUCTURED_TOP_P", "0.9"))
FORCE_FRESH_CODEGEN = os.getenv("FORCE_FRESH_CODEGEN", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SKIP_PLAN_VALIDATION_CHECKS = os.getenv("SKIP_PLAN_VALIDATION_CHECKS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

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

_UNICODE_MATH_TRANSLATIONS = {
    ord("−"): "-",
    ord("–"): "-",
    ord("—"): "-",
    ord("×"): "*",
    ord("÷"): "/",
    ord("π"): "pi",
    ord("⁰"): "^0",
    ord("¹"): "^1",
    ord("²"): "^2",
    ord("³"): "^3",
    ord("⁴"): "^4",
    ord("⁵"): "^5",
    ord("⁶"): "^6",
    ord("⁷"): "^7",
    ord("⁸"): "^8",
    ord("⁹"): "^9",
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
- FOR TRIGONOMETRY: Use 'unit_circle' only when unit-circle mechanics are explicitly requested.
    For sine/cosine graph-property explanations (amplitude, frequency, phase, period), prefer
    'trig_waves' or 'draw_curve'.
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

_PROMPT_COLOR_KEYWORDS = {
    "blue": "BLUE",
    "green": "GREEN",
    "teal": "TEAL",
    "yellow": "YELLOW",
    "gold": "GOLD",
    "red": "RED",
    "maroon": "MAROON",
    "orange": "ORANGE",
    "purple": "PURPLE",
    "white": "WHITE",
}

_STYLE_KEYWORDS = {
    "3b1b": "3b1b",
    "modern": "modern",
    "minimalist": "minimalist",
    "dark": "dark",
}

T5_STRICT_MATH_JSON_PROMPT = """You are a strict mathematical and visualization assistant.
Return ONLY valid JSON with EXACTLY this schema and no extra keys:
{
    "type": "matrix_multiplication|trigonometry_graph|algebra_solver|expression_evaluation|general_explanation",
    "input": "original user input",
    "intent": "short description of what user wants",
    "entities": {
        "numbers": [],
        "expressions": [],
        "objects": [],
        "keywords": []
    },
    "parameters": {
        "function": null,
        "range": null,
        "matrix_A": null,
        "matrix_B": null,
        "equation": null
    },
    "steps": [],
    "result": null,
    "visualization": {
        "scene_type": null,
        "elements": [],
        "animations": []
    }
}

Rules:
1. Detect exactly one supported type.
2. Fill all fields. Keep unused parameters as null.
3. Never invent numbers; only use input values or directly computed values.
4. For calculations, include ordered step-by-step in "steps".
5. For graph tasks, set parameters.function and parameters.range.
6. For explanation tasks, return ordered conceptual steps.
7. Output deterministic JSON only.
8. For matrix_multiplication, set parameters.matrix_A and parameters.matrix_B.
9. For algebra_solver, set parameters.equation and put final solution in result.
10. For expression_evaluation, put the expression string in entities.expressions[0].

Input: {user_input}
Output:
"""

_SUPPORTED_MATH_JSON_TYPES = {
    "matrix_multiplication",
    "trigonometry_graph",
    "algebra_solver",
    "expression_evaluation",
    "general_explanation",
}

_ALLOWED_TRIG_FEATURES = {"grid", "labels", "peaks"}

_T5_UNIFIED_PARAMETER_KEYS = {
    "function",
    "range",
    "matrix_A",
    "matrix_B",
    "equation",
}

_T5_UNIFIED_ENTITY_KEYS = {
    "numbers",
    "expressions",
    "objects",
    "keywords",
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


def _extract_user_requirements(user_prompt: str) -> Dict[str, Any]:
    """Extract explicit user constraints so the planner can preserve intent faithfully."""
    cleaned = _normalize_math_text(_compact_prompt_text(user_prompt))
    lower = cleaned.lower()

    requirements: Dict[str, Any] = {
        "plot_request": bool(re.search(r"\b(plot|graph|draw|curve|function)\b", lower)),
        "solve_request": bool(
            re.search(r"\b(solve|equation|roots?|zeros?|x-intercepts?)\b", lower)
        ),
        "compare_request": bool(
            re.search(r"\b(compare|versus|vs\.?|difference\s+between)\b", lower)
        ),
        "requested_equation": "",
        "requested_equations": [],
        "requested_algebra_equation": "",
        "requested_x_range": [],
        "requested_colors": [],
        "style_hint": "",
        "unit_circle_request": bool(re.search(r"\bunit[\s\-]?circle\b", lower)),
        "wave_mapping_request": bool(
            re.search(r"\b(wave|waveform|mapping|trace|tracing|synchronized)\b", lower)
        ),
        "projection_lines_request": bool(re.search(r"\b(projection|projection lines?)\b", lower)),
        "rotating_radius_request": bool(
            re.search(r"\b(rotating\s+radius|radius\s+rotation|rotating)\b", lower)
        ),
        "terms": _extract_key_terms(cleaned, max_terms=5),
    }

    equation_matches = re.finditer(
        (
            r"(?:y|f\(x\))\s*=\s*(.+?)"
            r"(?=(?:\s+and\s+(?:y|f\(x\))\s*=)|(?:\s+from\s+)|(?:\s+for\s+)|[\.,;]|$)"
        ),
        cleaned,
        re.IGNORECASE,
    )
    requested_equations: List[str] = []
    for match in equation_matches:
        eq = match.group(1).strip()
        if not eq:
            continue
        eq_text = f"y = {eq}"
        if eq_text not in requested_equations:
            requested_equations.append(eq_text)

    # Fallback extraction for prompts that mention trig curves without explicit y= prefixes.
    if not requested_equations and requirements["plot_request"]:
        if re.search(r"\bsin\s*\(", lower):
            requested_equations.append("y = sin(x)")
        if re.search(r"\bcos\s*\(", lower):
            requested_equations.append("y = cos(x)")

    if requested_equations:
        requirements["requested_equations"] = requested_equations
        requirements["requested_equation"] = requested_equations[0]
        requirements["plot_request"] = True

    algebra_equation = _extract_equation_from_prompt(cleaned)
    if algebra_equation:
        requirements["requested_algebra_equation"] = algebra_equation
        requirements["solve_request"] = True
        if not requirements["requested_equation"]:
            requirements["requested_equation"] = algebra_equation

    range_match = re.search(
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:[\.;,]|$)",
        cleaned,
        re.IGNORECASE,
    )
    if range_match:
        requirements["requested_x_range"] = _coerce_range(
            [range_match.group(1).strip(), range_match.group(2).strip()],
            _PLOT_DEFAULT_X_RANGE,
        )

    colors: List[str] = []
    for token, canonical in _PROMPT_COLOR_KEYWORDS.items():
        if re.search(rf"\b{re.escape(token)}\b", lower) and canonical not in colors:
            colors.append(canonical)
    requirements["requested_colors"] = colors

    for token, canonical in _STYLE_KEYWORDS.items():
        if re.search(rf"\b{re.escape(token)}\b", lower):
            requirements["style_hint"] = canonical
            break

    if len(requested_equations) >= 2:
        requirements["compare_request"] = True

    requirements["single_curve_request"] = bool(
        len(requested_equations) == 1
        and requirements["plot_request"]
        and not requirements["compare_request"]
    )
    requirements["multi_curve_request"] = bool(
        len(requested_equations) >= 2 and requirements["plot_request"]
    )

    normalized_eqs = [_normalize_equation_for_compare(eq) for eq in requested_equations]
    requirements["contains_sine"] = any("np.sin" in eq for eq in normalized_eqs if eq)
    requirements["contains_cosine"] = any("np.cos" in eq for eq in normalized_eqs if eq)
    requirements["high_confidence_trig_mapping"] = bool(
        (requirements["unit_circle_request"] or requirements["wave_mapping_request"])
        and requirements["contains_sine"]
        and requirements["contains_cosine"]
    )
    requirements["equation_graph_request"] = bool(
        requirements.get("solve_request")
        and requirements.get("plot_request")
        and bool(requirements.get("requested_algebra_equation"))
    )

    return requirements


def _format_user_requirements_for_planner(requirements: Dict[str, Any]) -> str:
    """Convert extracted requirements into hard constraints for the planner prompt."""
    if not requirements:
        return ""

    lines: List[str] = []

    equations = [str(eq).strip() for eq in (requirements.get("requested_equations") or []) if eq]
    if len(equations) > 1:
        lines.append(f"- Preserve all requested equations exactly: {' ; '.join(equations)}")

    equation = str(requirements.get("requested_equation") or "").strip()
    if equation and not equations:
        lines.append(f"- Preserve this equation exactly: {equation}")

    x_range = requirements.get("requested_x_range")
    if isinstance(x_range, list) and len(x_range) == 2:
        lines.append(f"- Use x-range from {x_range[0]} to {x_range[1]}")

    colors = requirements.get("requested_colors") or []
    if colors:
        lines.append(f"- Respect requested color hints: {', '.join(colors)}")

    style_hint = str(requirements.get("style_hint") or "").strip()
    if style_hint:
        lines.append(f"- Use style preset: {style_hint}")

    if requirements.get("compare_request"):
        lines.append("- Provide a direct visual comparison (side-by-side or overlaid).")

    if requirements.get("high_confidence_trig_mapping"):
        lines.append(
            "- Include unit-circle mechanics with rotating radius, projection lines, and "
            "synchronized sine/cosine waveform tracing."
        )

    return "\n".join(lines)


def _requirements_preview_for_metadata(requirements: Dict[str, Any]) -> Dict[str, Any]:
    if not requirements:
        return {}

    return {
        "plot_request": bool(requirements.get("plot_request")),
        "compare_request": bool(requirements.get("compare_request")),
        "requested_equation": str(requirements.get("requested_equation") or "")[:120],
        "requested_equations": [
            str(eq)[:120] for eq in list(requirements.get("requested_equations") or [])[:4]
        ],
        "requested_x_range": requirements.get("requested_x_range") or [],
        "requested_colors": list(requirements.get("requested_colors") or []),
        "style_hint": str(requirements.get("style_hint") or ""),
        "solve_request": bool(requirements.get("solve_request")),
        "requested_algebra_equation": str(requirements.get("requested_algebra_equation") or "")[
            :120
        ],
        "equation_graph_request": bool(requirements.get("equation_graph_request")),
        "high_confidence_trig_mapping": bool(requirements.get("high_confidence_trig_mapping")),
    }


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


def _normalize_math_text(raw_text: Any) -> str:
    text = str(raw_text or "")
    text = text.translate(_UNICODE_MATH_TRANSLATIONS)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_equation_from_prompt(user_prompt: str) -> str:
    """Extract an explicit algebraic equation like 2x^2 - 4x - 6 = 0 from free text."""
    prompt = _normalize_math_text(user_prompt)
    if not prompt:
        return ""

    solve_match = re.search(
        (
            r"\b(?:solve|find(?:\s+the)?\s+(?:roots?|zeros?)|roots?\s+of|zeros?\s+of|equation)\b"
            r"[:\s]*(.+?=.+?)(?=\s+\b(?:and|with|using|where|for|graph|plot|explain|show|visually)\b|[\.,;]|$)"
        ),
        prompt,
        re.IGNORECASE,
    )
    candidates: List[str] = []
    if solve_match:
        candidates.append(_compact_prompt_text(solve_match.group(1)))

    for match in re.finditer(
        r"([A-Za-z0-9\^\+\-\*/\.\(\)\s]+=[A-Za-z0-9\^\+\-\*/\.\(\)\s]+)",
        prompt,
    ):
        candidates.append(_compact_prompt_text(match.group(1)))

    for candidate in candidates:
        normalized = re.sub(
            r"^(?:solve|equation|find(?:\s+the)?\s+(?:roots?|zeros?)\s+of)\s*",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip(" :")
        normalized = normalized.rstrip(".,;")
        if "=" in normalized and re.search(r"[A-Za-z]", normalized):
            return normalized

    return ""


def _equation_to_plot_expression(equation: str) -> Optional[str]:
    normalized_equation = _normalize_math_text(equation)
    if not normalized_equation:
        return None

    if "=" in normalized_equation:
        left, right = normalized_equation.split("=", 1)
        left = left.strip()
        right = right.strip()
        if left and right:
            return _sanitize_plot_expression(f"({left})-({right})")

    return _sanitize_plot_expression(normalized_equation)


def _safe_eval_sanitized_expression(expression: str, x_value: float) -> Optional[float]:
    np_namespace = np if np is not None else math
    try:
        result = eval(  # nosec B307 - expression is constrained by _sanitize_plot_expression
            expression,
            {"__builtins__": {}},
            {"x": float(x_value), "np": np_namespace, "math": math},
        )
        if hasattr(result, "item"):
            result = result.item()
        value = float(result)
        if not math.isfinite(value):
            return None
        return value
    except Exception:
        return None


def _infer_linear_or_quadratic_coefficients(
    expression: str,
) -> Optional[tuple[float, float, float]]:
    """Infer coefficients for f(x)=ax^2+bx+c when expression behaves like polynomial <= degree 2."""
    f0 = _safe_eval_sanitized_expression(expression, 0.0)
    f1 = _safe_eval_sanitized_expression(expression, 1.0)
    f_1 = _safe_eval_sanitized_expression(expression, -1.0)
    f2 = _safe_eval_sanitized_expression(expression, 2.0)
    if None in {f0, f1, f_1, f2}:
        return None

    c = float(f0)
    b = (float(f1) - float(f_1)) / 2.0
    a = float(f1) - b - c

    predicted_f2 = (a * 4.0) + (b * 2.0) + c
    if abs(predicted_f2 - float(f2)) > 1e-4:
        return None

    if abs(a) < 1e-10 and abs(b) < 1e-10:
        return None

    return a, b, c


def _derive_equation_solution(equation: str) -> Optional[Dict[str, Any]]:
    """Derive deterministic solving steps for linear/quadratic equations."""
    normalized_equation = _normalize_math_text(_compact_prompt_text(equation))
    if not normalized_equation or "=" not in normalized_equation:
        return None

    expression = _equation_to_plot_expression(normalized_equation)
    if not expression:
        return None

    coeffs = _infer_linear_or_quadratic_coefficients(expression)
    if coeffs is None:
        return None

    a, b, c = coeffs
    fmt = _format_numeric_for_calculation

    steps: List[str] = [normalized_equation]
    real_roots: List[float] = []

    if abs(a) < 1e-10:
        if abs(b) < 1e-10:
            return None

        root = -c / b
        steps.extend(
            [
                f"Linear form: {fmt(b)}x + {fmt(c)} = 0",
                f"{fmt(b)}x = {fmt(-c)}",
                f"x = {fmt(root)}",
            ]
        )
        result_text = f"x = {fmt(root)}"
        real_roots = [float(root)]
    else:
        discriminant = (b * b) - (4.0 * a * c)
        steps.extend(
            [
                f"Identify coefficients: a={fmt(a)}, b={fmt(b)}, c={fmt(c)}",
                f"Discriminant Delta = b^2 - 4ac = {fmt(discriminant)}",
            ]
        )

        if discriminant > 1e-10:
            sqrt_d = math.sqrt(discriminant)
            x1 = (-b + sqrt_d) / (2.0 * a)
            x2 = (-b - sqrt_d) / (2.0 * a)
            ordered_roots = sorted([float(x1), float(x2)])
            real_roots = ordered_roots
            steps.extend(
                [
                    "x = (-b ± sqrt(Delta)) / (2a)",
                    f"x1 = {fmt(ordered_roots[0])}, x2 = {fmt(ordered_roots[1])}",
                ]
            )
            result_text = f"x = {fmt(ordered_roots[0])} or x = {fmt(ordered_roots[1])}"
        elif abs(discriminant) <= 1e-10:
            root = -b / (2.0 * a)
            real_roots = [float(root)]
            steps.extend(["x = -b / (2a)", f"x = {fmt(root)}"])
            result_text = f"x = {fmt(root)}"
        else:
            real_part = -b / (2.0 * a)
            imag_part = math.sqrt(-discriminant) / abs(2.0 * a)
            steps.extend(
                [
                    "Delta < 0, so there are no real x-intercepts.",
                    f"x = {fmt(real_part)} ± {fmt(imag_part)}i",
                ]
            )
            result_text = f"x = {fmt(real_part)} ± {fmt(imag_part)}i"

    return {
        "equation": normalized_equation,
        "expression": expression,
        "steps": steps,
        "result": result_text,
        "real_roots": real_roots,
        "coefficients": {
            "a": _normalize_numeric_value(a),
            "b": _normalize_numeric_value(b),
            "c": _normalize_numeric_value(c),
        },
    }


def _pick_equation_plot_range(real_roots: List[float], requested_range: Any) -> List[float]:
    if isinstance(requested_range, (list, tuple)) and len(requested_range) == 2:
        return _coerce_range(requested_range, [-6.0, 6.0])

    if real_roots:
        lo = min(real_roots)
        hi = max(real_roots)
        span = max(1.0, hi - lo)
        padding = max(2.5, 0.8 * span)
        return [round(lo - padding, 4), round(hi + padding, 4)]

    return [-6.0, 6.0]


def _estimate_equation_y_range(expression: str, x_range: List[float]) -> List[float]:
    sample_x = [x_range[0], x_range[1], 0.0, (x_range[0] + x_range[1]) / 2.0]
    values: List[float] = []
    for x_value in sample_x:
        value = _safe_eval_sanitized_expression(expression, x_value)
        if value is None or abs(value) > 1e6:
            continue
        values.append(value)

    if not values:
        return [-10.0, 10.0]

    min_y = min(values)
    max_y = max(values)
    span = max(1.0, max_y - min_y)
    padding = max(1.5, 0.25 * span)
    return [round(min_y - padding, 4), round(max_y + padding, 4)]


def _canonical_plot_color(raw_color: Any) -> str:
    c = str(raw_color or "BLUE").strip().upper().replace(" ", "_")
    return c if c in _SAFE_PLOT_COLOR_TOKENS else "BLUE"


def _parse_t5_structured_output(raw_output: str) -> Optional[Dict[str, Any]]:
    """Parse raw T5 output into a JSON-like dict."""
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
    normalized_text = _normalize_math_text(text)
    function_match = re.search(
        r"(?:function|expression)\s*[:=]\s*([^,]+)",
        normalized_text,
        re.IGNORECASE,
    )
    range_match = re.search(r"(?:range|x_range)\s*[:=]\s*\[([^\]]+)\]", text, re.IGNORECASE)
    parsed: Dict[str, Any] = {}

    if function_match:
        parsed["function"] = function_match.group(1).strip()
    else:
        equation_match = re.search(
            r"(?:y|f\(x\))\s*=\s*(.+?)(?:\s+(?:from|for)\s+|$)",
            normalized_text,
            re.IGNORECASE,
        )
        if equation_match:
            parsed["function"] = equation_match.group(1).strip()

    equation_match = re.search(
        (
            r"\b(?:solve|find(?:\s+the)?\s+(?:roots?|zeros?)|roots?\s+of|zeros?\s+of|equation)\b"
            r"[:\s]*(.+?=.+?)(?=\s+\b(?:and|with|using|where|for|graph|plot|explain|show|visually)\b|[\.,;]|$)"
        ),
        normalized_text,
        re.IGNORECASE,
    )
    if not equation_match:
        equation_match = re.search(
            r"([A-Za-z0-9\^\+\-\*/\.\(\)\s]+=[A-Za-z0-9\^\+\-\*/\.\(\)\s]+)",
            normalized_text,
        )
    if equation_match:
        candidate = _compact_prompt_text(equation_match.group(1)).rstrip(".,;")
        if "=" in candidate and re.search(r"[A-Za-z]", candidate):
            parsed["type"] = "algebra_solver"
            parsed["equation"] = candidate

    if range_match:
        parsed["range"] = [p.strip() for p in range_match.group(1).split(",") if p.strip()]
    else:
        natural_range = re.search(
            r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:[\.;,]|$)",
            normalized_text,
            re.IGNORECASE,
        )
        if natural_range:
            parsed["range"] = [natural_range.group(1).strip(), natural_range.group(2).strip()]

            return parsed if parsed.get("function") or parsed.get("equation") else None


def _normalize_numeric_value(value: float) -> Any:
    rounded = round(float(value), 6)
    if float(rounded).is_integer():
        return int(rounded)
    return rounded


def _coerce_numeric_value(raw_value: Any) -> Optional[float]:
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if not stripped:
            return None
        sentinel = float("nan")
        parsed = _safe_eval_numeric_expression(stripped, sentinel)
        if math.isnan(parsed):
            return None
        return float(parsed)
    return None


def _coerce_range_strict(value: Any) -> Optional[List[float]]:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            parts = [p.strip() for p in stripped[1:-1].split(",")]
        else:
            parts = [p.strip() for p in stripped.split(",") if p.strip()]
    elif isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        return None

    if len(parts) < 2:
        return None

    start = _coerce_numeric_value(parts[0])
    end = _coerce_numeric_value(parts[1])
    if start is None or end is None or end <= start:
        return None

    return [round(start, 4), round(end, 4)]


def _coerce_numeric_matrix(raw_matrix: Any) -> Optional[List[List[Any]]]:
    if not isinstance(raw_matrix, list) or not raw_matrix:
        return None

    normalized: List[List[Any]] = []
    col_count: Optional[int] = None

    for raw_row in raw_matrix:
        if not isinstance(raw_row, list) or not raw_row:
            return None

        normalized_row: List[Any] = []
        for raw_cell in raw_row:
            parsed = _coerce_numeric_value(raw_cell)
            if parsed is None:
                return None
            normalized_row.append(_normalize_numeric_value(parsed))

        if col_count is None:
            col_count = len(normalized_row)
        elif col_count != len(normalized_row):
            return None

        normalized.append(normalized_row)

    return normalized


def _format_numeric_for_calculation(raw_value: Any) -> str:
    parsed = _coerce_numeric_value(raw_value)
    if parsed is None:
        return str(raw_value)
    return str(_normalize_numeric_value(parsed))


def _compute_matrix_multiplication_details(
    matrix_a: List[List[Any]], matrix_b: List[List[Any]]
) -> Optional[tuple[List[List[Any]], List[Dict[str, Any]]]]:
    if not matrix_a or not matrix_b:
        return None

    rows_a = len(matrix_a)
    cols_a = len(matrix_a[0])
    rows_b = len(matrix_b)
    cols_b = len(matrix_b[0])
    if cols_a != rows_b:
        return None

    final_matrix: List[List[Any]] = []
    steps: List[Dict[str, Any]] = []

    for row in range(rows_a):
        result_row: List[Any] = []
        for col in range(cols_b):
            total = 0.0
            terms: List[str] = []
            for idx in range(cols_a):
                a_val = float(matrix_a[row][idx])
                b_val = float(matrix_b[idx][col])
                total += a_val * b_val
                terms.append(
                    f"{_format_numeric_for_calculation(a_val)}*{_format_numeric_for_calculation(b_val)}"
                )

            numeric_result = _normalize_numeric_value(total)
            result_row.append(numeric_result)
            steps.append(
                {
                    "position": [row, col],
                    "calculation": " + ".join(terms),
                    "result": numeric_result,
                }
            )
        final_matrix.append(result_row)

    return final_matrix, steps


def _derive_trig_parameters_from_function(function_expr: str) -> Optional[Dict[str, Any]]:
    expr = re.sub(r"\s+", "", str(function_expr or ""))
    expr = re.sub(r"^(?:y|f\(x\))=", "", expr, flags=re.IGNORECASE)
    expr = expr.replace("np.", "")

    leading_sign = 1.0
    if expr.startswith("-"):
        leading_sign = -1.0
        expr = expr[1:]
    elif expr.startswith("+"):
        expr = expr[1:]

    pattern = re.compile(
        (
            r"^([+-]?(?:\d+(?:\.\d+)?|\.\d+))?\*?(sin|cos)\("
            r"([+-]?(?:\d+(?:\.\d+)?|\.\d+))?\*?x"
            r"(?:([+-](?:\d+(?:\.\d+)?|\.\d+)))?\)"
            r"([+-](?:\d+(?:\.\d+)?|\.\d+))?$"
        ),
        re.IGNORECASE,
    )
    match = pattern.match(expr)
    if not match:
        return None

    amp_raw, _, freq_raw, phase_raw, vertical_raw = match.groups()
    amplitude = leading_sign * (float(amp_raw) if amp_raw not in {None, ""} else 1.0)
    frequency = float(freq_raw) if freq_raw not in {None, ""} else 1.0
    if frequency == 0:
        return None

    vertical_shift = float(vertical_raw) if vertical_raw not in {None, ""} else 0.0
    if phase_raw in {None, "", "+0", "-0"}:
        phase_shift = "0"
    else:
        phase_shift = f"-({phase_raw})/{_format_numeric_for_calculation(frequency)}"

    return {
        "amplitude": _normalize_numeric_value(abs(amplitude)),
        "frequency": _normalize_numeric_value(abs(frequency)),
        "phase_shift": phase_shift,
        "vertical_shift": _normalize_numeric_value(vertical_shift),
    }


def _normalize_string_steps(raw_steps: Any) -> List[str]:
    if not isinstance(raw_steps, list):
        return []

    steps: List[str] = []
    for raw_step in raw_steps:
        text = _compact_prompt_text(str(raw_step or ""))
        if text:
            steps.append(text)
    return steps


def _normalize_string_list(raw_values: Any, max_items: int = 24) -> List[str]:
    if not isinstance(raw_values, list):
        return []

    items: List[str] = []
    for raw in raw_values:
        text = _compact_prompt_text(str(raw or ""))
        if text and text not in items:
            items.append(text)
        if len(items) >= max_items:
            break
    return items


def _coerce_number_list(raw_values: Any) -> List[Any]:
    if not isinstance(raw_values, list):
        return []

    values: List[Any] = []
    seen: set[str] = set()
    for raw in raw_values:
        parsed = _coerce_numeric_value(raw)
        if parsed is None:
            continue
        normalized = _normalize_numeric_value(parsed)
        key = str(normalized)
        if key in seen:
            continue
        seen.add(key)
        values.append(normalized)
    return values


def _extract_unified_parameters(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_params = raw_payload.get("parameters")
    if not isinstance(raw_params, dict):
        return {}

    return {
        "function": raw_params.get("function"),
        "range": raw_params.get("range"),
        "matrix_A": raw_params.get("matrix_A"),
        "matrix_B": raw_params.get("matrix_B"),
        "equation": raw_params.get("equation"),
    }


def _default_intent_for_type(payload_type: str) -> str:
    defaults = {
        "matrix_multiplication": "Multiply two matrices and compute each output cell.",
        "trigonometry_graph": "Plot the requested trigonometric function over the given range.",
        "algebra_solver": "Solve the equation step by step.",
        "expression_evaluation": "Evaluate the arithmetic expression using order of operations.",
        "general_explanation": "Explain the requested topic in ordered steps.",
    }
    return defaults.get(payload_type, "Interpret the math request and respond structurally.")


def _normalize_unified_entities(raw_payload: Dict[str, Any], input_text: str) -> Dict[str, Any]:
    raw_entities = raw_payload.get("entities")
    if not isinstance(raw_entities, dict):
        raw_entities = {}

    entities = {
        "numbers": _coerce_number_list(raw_entities.get("numbers")),
        "expressions": _normalize_string_list(raw_entities.get("expressions")),
        "objects": _normalize_string_list(raw_entities.get("objects")),
        "keywords": _normalize_string_list(raw_entities.get("keywords")),
    }

    if not entities["keywords"]:
        entities["keywords"] = _extract_key_terms(input_text, max_terms=6)
    return entities


def _normalize_unified_visualization(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_visualization = raw_payload.get("visualization")
    if not isinstance(raw_visualization, dict):
        raw_visualization = {}

    scene_type = raw_visualization.get("scene_type")
    scene_type_value = _compact_prompt_text(str(scene_type or "")) or None

    return {
        "scene_type": scene_type_value,
        "elements": _normalize_string_list(raw_visualization.get("elements"), max_items=16),
        "animations": _normalize_string_list(raw_visualization.get("animations"), max_items=16),
    }


def _new_unified_payload_shell(
    payload_type: str, user_prompt: str, raw_payload: Dict[str, Any]
) -> Dict[str, Any]:
    input_text = _compact_prompt_text(str(raw_payload.get("input") or user_prompt or ""))
    intent_text = _compact_prompt_text(str(raw_payload.get("intent") or ""))
    if not intent_text:
        intent_text = _default_intent_for_type(payload_type)

    return {
        "type": payload_type,
        "input": input_text,
        "intent": intent_text,
        "entities": _normalize_unified_entities(raw_payload, input_text),
        "parameters": {
            "function": None,
            "range": None,
            "matrix_A": None,
            "matrix_B": None,
            "equation": None,
        },
        "steps": [],
        "result": None,
        "visualization": _normalize_unified_visualization(raw_payload),
    }


def _normalize_t5_math_payload(
    user_prompt: str, raw_payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_payload, dict):
        return None

    unified_params = _extract_unified_parameters(raw_payload)

    payload_type = _compact_prompt_text(str(raw_payload.get("type") or "")).lower()
    if not payload_type:
        if (
            unified_params.get("function")
            or raw_payload.get("function")
            or raw_payload.get("expression")
        ):
            payload_type = "trigonometry_graph"
        elif unified_params.get("matrix_A") or raw_payload.get("matrix_A"):
            payload_type = "matrix_multiplication"
        elif unified_params.get("equation") or raw_payload.get("equation"):
            payload_type = "algebra_solver"
        elif raw_payload.get("expression"):
            payload_type = "expression_evaluation"
        else:
            return None

    if payload_type not in _SUPPORTED_MATH_JSON_TYPES:
        return None

    payload = _new_unified_payload_shell(payload_type, user_prompt, raw_payload)

    if payload_type == "matrix_multiplication":
        matrix_a = _coerce_numeric_matrix(
            unified_params.get("matrix_A") or raw_payload.get("matrix_A")
        )
        matrix_b = _coerce_numeric_matrix(
            unified_params.get("matrix_B") or raw_payload.get("matrix_B")
        )
        if matrix_a is None or matrix_b is None:
            return None

        details = _compute_matrix_multiplication_details(matrix_a, matrix_b)
        if details is None:
            return None
        final_matrix, structured_steps = details

        step_lines: List[str] = []
        for step in structured_steps:
            pos = step.get("position") or [0, 0]
            row_idx = int(pos[0]) + 1 if isinstance(pos, list) and len(pos) > 0 else 1
            col_idx = int(pos[1]) + 1 if isinstance(pos, list) and len(pos) > 1 else 1
            calculation = str(step.get("calculation") or "").strip()
            result = _format_numeric_for_calculation(step.get("result"))
            if calculation:
                step_lines.append(f"C[{row_idx},{col_idx}] = {calculation} = {result}")

        payload["parameters"]["matrix_A"] = matrix_a
        payload["parameters"]["matrix_B"] = matrix_b
        payload["steps"] = step_lines
        payload["result"] = final_matrix

        if not payload["entities"]["numbers"]:
            numeric_terms: List[Any] = []
            for row in matrix_a + matrix_b + final_matrix:
                numeric_terms.extend(row)
            payload["entities"]["numbers"] = _coerce_number_list(numeric_terms)

        if not payload["visualization"]["scene_type"]:
            payload["visualization"]["scene_type"] = "matrix_multiplication"
        if not payload["visualization"]["elements"]:
            payload["visualization"]["elements"] = [
                "matrix_A",
                "matrix_B",
                "dot_product_steps",
                "final_matrix",
            ]
        if not payload["visualization"]["animations"]:
            payload["visualization"]["animations"] = [
                "highlight_row_column",
                "compute_entry",
                "show_result",
            ]

        return payload

    if payload_type == "trigonometry_graph":
        function = _compact_prompt_text(
            str(
                unified_params.get("function")
                or raw_payload.get("function")
                or raw_payload.get("expression")
                or ""
            )
        )
        if not function:
            return None

        raw_range = unified_params.get("range") or raw_payload.get("range")
        if raw_range is None or raw_range == "" or raw_range == []:
            natural_range = re.search(
                r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:[\.;,]|$)",
                user_prompt,
                re.IGNORECASE,
            )
            if natural_range:
                raw_range = [natural_range.group(1).strip(), natural_range.group(2).strip()]

        graph_range = _coerce_range_strict(raw_range)
        if graph_range is None:
            return None

        amplitude = _coerce_numeric_value(raw_payload.get("amplitude"))
        frequency = _coerce_numeric_value(raw_payload.get("frequency"))
        vertical_shift = _coerce_numeric_value(raw_payload.get("vertical_shift"))
        phase_shift = _compact_prompt_text(str(raw_payload.get("phase_shift") or ""))

        derived = _derive_trig_parameters_from_function(function)
        if derived is not None:
            if amplitude is None:
                amplitude = float(derived["amplitude"])
            if frequency is None:
                frequency = float(derived["frequency"])
            if vertical_shift is None:
                vertical_shift = float(derived["vertical_shift"])
            if not phase_shift:
                phase_shift = str(derived["phase_shift"])

        if amplitude is None or frequency is None or vertical_shift is None:
            return None
        if not phase_shift:
            phase_shift = "0"

        raw_features = raw_payload.get("features")
        if not isinstance(raw_features, list):
            raw_features = []

        features: List[str] = []
        for raw_feature in raw_features:
            token = _compact_prompt_text(str(raw_feature or "")).lower()
            if token in _ALLOWED_TRIG_FEATURES and token not in features:
                features.append(token)
        if not features:
            features = ["grid", "labels"]

        payload["parameters"]["function"] = function
        payload["parameters"]["range"] = graph_range

        steps = _normalize_string_steps(raw_payload.get("steps"))
        if not steps:
            steps = [
                f"Use function f(x) = {function}",
                f"Plot over x in [{graph_range[0]}, {graph_range[1]}]",
                (
                    "Extract waveform parameters: "
                    f"amplitude={_normalize_numeric_value(amplitude)}, "
                    f"frequency={_normalize_numeric_value(frequency)}, "
                    f"phase_shift={phase_shift}, "
                    f"vertical_shift={_normalize_numeric_value(vertical_shift)}"
                ),
            ]
        payload["steps"] = steps
        payload["result"] = {
            "amplitude": _normalize_numeric_value(amplitude),
            "frequency": _normalize_numeric_value(frequency),
            "phase_shift": phase_shift,
            "vertical_shift": _normalize_numeric_value(vertical_shift),
            "features": features,
        }

        if function not in payload["entities"]["expressions"]:
            payload["entities"]["expressions"].insert(0, function)
        if not payload["visualization"]["scene_type"]:
            payload["visualization"]["scene_type"] = "curve_plot"
        if not payload["visualization"]["elements"]:
            payload["visualization"]["elements"] = ["axes", "curve", *features]
        if not payload["visualization"]["animations"]:
            payload["visualization"]["animations"] = ["draw_axes", "draw_curve", "label_features"]

        return payload

    if payload_type == "algebra_solver":
        equation = _compact_prompt_text(
            str(unified_params.get("equation") or raw_payload.get("equation") or "")
        )
        if not equation:
            equation = _extract_equation_from_prompt(user_prompt)

        steps = _normalize_string_steps(raw_payload.get("steps"))
        solution = _compact_prompt_text(
            str(raw_payload.get("result") or raw_payload.get("solution") or "")
        )

        derived_solution = _derive_equation_solution(equation) if equation else None
        if not steps and derived_solution:
            steps = list(derived_solution.get("steps") or [])
        if not solution and derived_solution:
            solution = _compact_prompt_text(str(derived_solution.get("result") or ""))
        if not equation and derived_solution:
            equation = _compact_prompt_text(str(derived_solution.get("equation") or ""))

        if not equation or not steps or not solution:
            return None

        payload["parameters"]["equation"] = equation
        payload["steps"] = steps
        payload["result"] = solution
        if equation not in payload["entities"]["expressions"]:
            payload["entities"]["expressions"].insert(0, equation)
        if not payload["visualization"]["scene_type"]:
            payload["visualization"]["scene_type"] = "algebra_steps"
        if not payload["visualization"]["elements"]:
            payload["visualization"]["elements"] = ["equation", "transform_steps", "solution"]
        if not payload["visualization"]["animations"]:
            payload["visualization"]["animations"] = [
                "write_equation",
                "transform",
                "highlight_solution",
            ]
        return payload

    if payload_type == "expression_evaluation":
        expression = _compact_prompt_text(str(raw_payload.get("expression") or ""))
        if not expression:
            expressions = payload["entities"].get("expressions") or []
            if expressions:
                expression = _compact_prompt_text(str(expressions[0]))
        steps = _normalize_string_steps(raw_payload.get("steps"))
        result_num = _coerce_numeric_value(raw_payload.get("result"))
        if result_num is None:
            result_num = _coerce_numeric_value(raw_payload.get("solution"))
        if result_num is None and expression:
            result_num = _coerce_numeric_value(expression)

        if not expression or not steps or result_num is None:
            return None

        payload["steps"] = steps
        payload["result"] = _normalize_numeric_value(result_num)
        if expression not in payload["entities"]["expressions"]:
            payload["entities"]["expressions"].insert(0, expression)
        if not payload["visualization"]["scene_type"]:
            payload["visualization"]["scene_type"] = "expression_steps"
        if not payload["visualization"]["elements"]:
            payload["visualization"]["elements"] = ["expression", "arithmetic_steps", "result"]
        if not payload["visualization"]["animations"]:
            payload["visualization"]["animations"] = [
                "write_expression",
                "step_transform",
                "show_result",
            ]
        return payload

    if payload_type == "general_explanation":
        topic = _compact_prompt_text(
            str(raw_payload.get("topic") or raw_payload.get("intent") or payload["input"] or "")
        )
        steps = _normalize_string_steps(raw_payload.get("steps"))
        if not topic or not steps:
            return None

        payload["intent"] = _compact_prompt_text(
            str(raw_payload.get("intent") or f"Explain {topic}")
        )
        payload["steps"] = steps
        payload["result"] = None
        if topic not in payload["entities"]["objects"]:
            payload["entities"]["objects"].insert(0, topic)
        if not payload["visualization"]["scene_type"]:
            payload["visualization"]["scene_type"] = "general_explanation"
        if not payload["visualization"]["elements"]:
            payload["visualization"]["elements"] = ["title", "bullet_steps"]
        if not payload["visualization"]["animations"]:
            payload["visualization"]["animations"] = ["write_title", "staggered_reveal"]
        return payload

    return None


def _build_step_scene_from_lines(
    scene_id: str, title: str, lines: List[str], narration: str
) -> AnimationScene:
    safe_scene_id = _sanitize_identifier(scene_id, "scene")
    title_id = f"{safe_scene_id}_title"

    objects: List[AnimationObject] = [
        AnimationObject(
            id=title_id,
            type="text",
            parameters={"text": title, "position": [0, 2.5, 0], "font_size": 34},
        )
    ]
    animations: List[AnimationStep] = [
        AnimationStep(object_id=title_id, action="write", duration=1.0)
    ]

    row_index = 0
    for raw_line in lines:
        line = _compact_prompt_text(str(raw_line or ""))
        if not line:
            continue

        row_index += 1
        if row_index > 7:
            break

        obj_id = f"{safe_scene_id}_line_{row_index}"
        obj_type = "math_tex" if re.search(r"[=+\-*/^\\]", line) else "text"
        y_pos = round(1.6 - ((row_index - 1) * 0.68), 2)
        objects.append(
            AnimationObject(
                id=obj_id,
                type=obj_type,
                parameters={"text": line, "position": [0, y_pos, 0], "font_size": 28},
            )
        )
        animations.append(AnimationStep(object_id=obj_id, action="fade_in", duration=0.85))

    return AnimationScene(
        scene_id=safe_scene_id,
        template="generic",
        objects=objects,
        animations=animations,
        narration=narration,
    )


def _build_plan_from_t5_math_payload(
    user_prompt: str, payload: Dict[str, Any]
) -> Optional[AnimationPlan]:
    payload_type = str(payload.get("type") or "").strip().lower()
    payload_params = (
        payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    )
    payload_entities = payload.get("entities") if isinstance(payload.get("entities"), dict) else {}

    def _param(key: str, fallback_key: Optional[str] = None) -> Any:
        value = payload_params.get(key)
        if value not in (None, "", []):
            return value
        if fallback_key:
            return payload.get(fallback_key)
        return payload.get(key)

    if payload_type == "trigonometry_graph":
        plot_plan = _build_plot_plan_from_structured(
            user_prompt,
            {
                "function": _param("function", "function"),
                "range": _param("range", "range"),
                "color": "GREEN",
            },
        )
        if plot_plan is None:
            return None

        params = dict(plot_plan.parameters or {})
        params["structured_math_json"] = payload
        plot_plan.parameters = params
        return plot_plan

    if payload_type == "matrix_multiplication":
        matrix_a = _coerce_numeric_matrix(_param("matrix_A", "matrix_A"))
        matrix_b = _coerce_numeric_matrix(_param("matrix_B", "matrix_B"))
        if matrix_a is None or matrix_b is None:
            return None

        step_lines: List[str] = []
        for step in payload.get("steps") or []:
            if isinstance(step, str):
                line = _compact_prompt_text(step)
                if line:
                    step_lines.append(line)
                continue

            if isinstance(step, dict):
                pos = step.get("position") or [0, 0]
                row_idx = int(pos[0]) + 1 if isinstance(pos, list) and len(pos) > 0 else 1
                col_idx = int(pos[1]) + 1 if isinstance(pos, list) and len(pos) > 1 else 1
                calculation = str(step.get("calculation") or "").strip()
                result = _format_numeric_for_calculation(step.get("result"))
                if calculation:
                    step_lines.append(f"C[{row_idx},{col_idx}] = {calculation} = {result}")

        details = _compute_matrix_multiplication_details(matrix_a, matrix_b)
        if details is None:
            return None
        computed_final_matrix, computed_steps = details

        if not step_lines:
            for step in computed_steps:
                pos = step.get("position") or [0, 0]
                row_idx = int(pos[0]) + 1 if isinstance(pos, list) and len(pos) > 0 else 1
                col_idx = int(pos[1]) + 1 if isinstance(pos, list) and len(pos) > 1 else 1
                calc = str(step.get("calculation") or "").strip()
                result = _format_numeric_for_calculation(step.get("result"))
                if calc:
                    step_lines.append(f"C[{row_idx},{col_idx}] = {calc} = {result}")

        raw_result_matrix = payload.get("result", payload.get("final_matrix"))
        final_matrix = _coerce_numeric_matrix(raw_result_matrix) or computed_final_matrix

        matrix_scene = AnimationScene(
            scene_id="matrix_compute",
            template="matrix_multiplication",
            parameters={
                "matrix_a": matrix_a,
                "matrix_b": matrix_b,
            },
            narration="Multiply matrix A and matrix B using row-column dot products.",
        )
        steps_scene = _build_step_scene_from_lines(
            "matrix_steps",
            "Dot-Product Steps",
            step_lines,
            "Show each matrix cell computation explicitly.",
        )
        result_scene = AnimationScene(
            scene_id="matrix_result",
            template="generic",
            objects=[
                AnimationObject(
                    id="matrix_result_title",
                    type="text",
                    parameters={"text": "Final Matrix", "position": [0, 2.3, 0], "font_size": 34},
                ),
                AnimationObject(
                    id="matrix_result_value",
                    type="matrix",
                    parameters={"entries": final_matrix, "position": [0, 0.4, 0]},
                ),
            ],
            animations=[
                AnimationStep(object_id="matrix_result_title", action="write", duration=1.0),
                AnimationStep(object_id="matrix_result_value", action="fade_in", duration=1.0),
            ],
            narration="Present the resulting matrix.",
        )
        return AnimationPlan(
            title="Matrix Multiplication",
            style="3b1b",
            template=None,
            parameters={"structured_math_json": payload},
            scenes=[matrix_scene, steps_scene, result_scene],
        )

    if payload_type == "algebra_solver":
        equation = _compact_prompt_text(str(_param("equation", "equation") or ""))
        steps = [str(s) for s in (payload.get("steps") or [])]
        solution_value = payload.get("result", payload.get("solution"))
        solution_text = _compact_prompt_text(str(solution_value or ""))

        derived_solution = _derive_equation_solution(equation) if equation else None
        if not steps and derived_solution:
            steps = [str(s) for s in (derived_solution.get("steps") or [])]
        if not solution_text and derived_solution:
            solution_text = _compact_prompt_text(str(derived_solution.get("result") or ""))
        if not equation and derived_solution:
            equation = _compact_prompt_text(str(derived_solution.get("equation") or ""))

        if not equation or not steps or not solution_text:
            return None

        if not steps or steps[0] != equation:
            steps = [equation] + steps

        steps_scene = _build_step_scene_from_lines(
            "algebra_steps",
            "Equation Solving",
            steps,
            "Solve the equation step by step.",
        )
        solution_scene = _build_step_scene_from_lines(
            "algebra_solution",
            "Solution",
            [solution_text],
            "State the final solution.",
        )

        include_graph = bool(
            re.search(r"\b(plot|graph|curve|visual)\b", user_prompt, re.IGNORECASE)
        )
        raw_visualization = payload.get("visualization") if isinstance(payload, dict) else {}
        if isinstance(raw_visualization, dict):
            scene_type = str(raw_visualization.get("scene_type") or "").lower()
            if any(token in scene_type for token in ("graph", "plot", "curve")):
                include_graph = True
            visual_elements = raw_visualization.get("elements") or []
            if isinstance(visual_elements, list):
                include_graph = include_graph or any(
                    str(el).lower() in {"graph", "curve", "axes", "x_intercepts"}
                    for el in visual_elements
                )

        scenes: List[AnimationScene] = [steps_scene]
        if include_graph and derived_solution and derived_solution.get("expression"):
            real_roots = [float(v) for v in (derived_solution.get("real_roots") or [])]
            x_range = _pick_equation_plot_range(real_roots, None)
            expression = str(derived_solution.get("expression") or "")
            y_range = _estimate_equation_y_range(expression, x_range)
            graph_scene = AnimationScene(
                scene_id="equation_graph",
                template="draw_curve",
                depends_on=[steps_scene.scene_id],
                parameters={
                    "expression": expression,
                    "x_range": x_range,
                    "y_range": y_range,
                    "color": "BLUE",
                    "label": "f(x)",
                },
                narration=(
                    "Plot f(x) where the equation is rewritten as f(x)=0. "
                    "The x-intercepts correspond to real roots."
                ),
            )
            scenes.append(graph_scene)
            solution_scene.depends_on = [graph_scene.scene_id]
        else:
            solution_scene.depends_on = [steps_scene.scene_id]

        scenes.append(solution_scene)

        return AnimationPlan(
            title="Algebra Solver",
            style="3b1b",
            template=None,
            parameters={"structured_math_json": payload},
            scenes=scenes,
        )

    if payload_type == "expression_evaluation":
        expression = _compact_prompt_text(str(payload.get("expression") or ""))
        if not expression:
            expressions = payload_entities.get("expressions")
            if isinstance(expressions, list) and expressions:
                expression = _compact_prompt_text(str(expressions[0]))
        if not expression:
            expression = _compact_prompt_text(str(payload.get("input") or "Expression"))

        eval_steps = [str(s) for s in (payload.get("steps") or [])]
        eval_steps.append(f"Result = {payload.get('result')}")

        evaluation_scene = _build_step_scene_from_lines(
            "expression_eval",
            f"Evaluate: {expression}",
            eval_steps,
            "Evaluate the expression using the shown arithmetic steps.",
        )

        return AnimationPlan(
            title="Expression Evaluation",
            style="3b1b",
            template=None,
            parameters={"structured_math_json": payload},
            scenes=[evaluation_scene],
        )

    if payload_type == "general_explanation":
        topic = _compact_prompt_text(
            str(
                payload.get("topic")
                or payload.get("intent")
                or payload.get("input")
                or "Concept Explanation"
            )
        )
        explanation_scene = _build_step_scene_from_lines(
            "general_explanation",
            topic,
            [str(s) for s in (payload.get("steps") or [])],
            "Explain the concept in ordered steps.",
        )

        return AnimationPlan(
            title=topic[:80],
            style="3b1b",
            template=None,
            parameters={"structured_math_json": payload},
            scenes=[explanation_scene],
        )

    return None


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


def _normalize_equation_for_compare(raw_expr: Any) -> str:
    expr = str(raw_expr or "").strip()
    if "=" in expr and not re.match(r"^\s*(?:y|f\(x\))\s*=", expr, re.IGNORECASE):
        normalized_equation = _equation_to_plot_expression(expr)
        return normalized_equation or ""
    if "=" in expr:
        expr = expr.split("=", 1)[1]
    normalized = _sanitize_plot_expression(expr)
    return normalized or ""


def _extract_curve_params_from_plan(plan: AnimationPlan) -> Dict[str, Any]:
    params = dict(plan.parameters or {})
    if params.get("expression"):
        return {
            "expression": params.get("expression"),
            "x_range": params.get("x_range"),
            "color": params.get("color"),
        }

    for scene in plan.scenes or []:
        if scene.template != "draw_curve":
            continue
        scene_params = dict(scene.parameters or {})
        if scene_params.get("expression"):
            return {
                "expression": scene_params.get("expression"),
                "x_range": scene_params.get("x_range"),
                "color": scene_params.get("color"),
            }

    return {}


def _extract_curve_expressions_from_plan(plan: AnimationPlan) -> List[str]:
    expressions: List[str] = []

    def _add_expression(raw_expr: Any) -> None:
        normalized = _normalize_equation_for_compare(raw_expr)
        if normalized and normalized not in expressions:
            expressions.append(normalized)

    plan_params = dict(plan.parameters or {})
    if plan.template in {"draw_curve", "trig_waves"}:
        _add_expression(plan_params.get("expression"))
    if plan.template == "trig_comparison":
        for fn in plan_params.get("functions", []) or []:
            _add_expression(f"y = {fn}(x)")

    for scene in plan.scenes or []:
        scene_params = dict(scene.parameters or {})
        if scene.template in {"draw_curve", "trig_waves"}:
            _add_expression(scene_params.get("expression"))
        elif scene.template == "trig_comparison":
            for fn in scene_params.get("functions", []) or []:
                _add_expression(f"y = {fn}(x)")

    return expressions


def _extract_curve_range_from_plan(plan: AnimationPlan) -> Any:
    plan_params = dict(plan.parameters or {})
    if isinstance(plan_params.get("x_range"), (list, tuple, str)):
        return plan_params.get("x_range")

    for scene in plan.scenes or []:
        scene_params = dict(scene.parameters or {})
        if isinstance(scene_params.get("x_range"), (list, tuple, str)):
            return scene_params.get("x_range")

    return None


def _extract_curve_colors_from_plan(plan: AnimationPlan) -> List[str]:
    colors: List[str] = []

    def _add_color(raw_color: Any) -> None:
        canonical = _canonical_plot_color(raw_color)
        if canonical and canonical not in colors:
            colors.append(canonical)

    plan_params = dict(plan.parameters or {})
    if plan_params.get("color"):
        _add_color(plan_params.get("color"))
    for c in plan_params.get("colors", []) or []:
        _add_color(c)

    for scene in plan.scenes or []:
        scene_params = dict(scene.parameters or {})
        if scene_params.get("color"):
            _add_color(scene_params.get("color"))
        for c in scene_params.get("colors", []) or []:
            _add_color(c)
        if scene.template == "unit_circle":
            _add_color(scene_params.get("color_sin"))
            _add_color(scene_params.get("color_cos"))

    return colors


def _ranges_are_close(expected: List[float], actual: Any, tolerance: float = 0.05) -> bool:
    if not isinstance(expected, list) or len(expected) != 2:
        return True
    if actual is None:
        return False

    actual_range = _coerce_range(actual, expected)
    return (
        abs(float(expected[0]) - float(actual_range[0])) <= tolerance
        and abs(float(expected[1]) - float(actual_range[1])) <= tolerance
    )


def _validate_plan_against_user_requirements(
    plan: AnimationPlan, requirements: Dict[str, Any]
) -> List[str]:
    """Check whether explicit user constraints survived planning."""
    violations: List[str] = []
    if not requirements:
        return violations

    if requirements.get("style_hint") and plan.style != requirements.get("style_hint"):
        violations.append("Plan style does not match requested style hint.")

    expected_equations = [
        str(eq).strip() for eq in (requirements.get("requested_equations") or []) if str(eq).strip()
    ]
    if not expected_equations and requirements.get("requested_equation"):
        expected_equations = [str(requirements.get("requested_equation") or "").strip()]

    if expected_equations:
        expected_norms = [
            _normalize_equation_for_compare(eq)
            for eq in expected_equations
            if _normalize_equation_for_compare(eq)
        ]
        actual_norms = _extract_curve_expressions_from_plan(plan)

        if not actual_norms:
            violations.append("Plan is missing requested equation curves for plotting.")
        else:
            missing = [eq for eq in expected_norms if eq and eq not in actual_norms]
            if missing:
                violations.append("Plan equations do not fully match user requested equations.")

    expected_range = requirements.get("requested_x_range")
    if expected_range and expected_equations:
        actual_range = _extract_curve_range_from_plan(plan)
        if not _ranges_are_close(expected_range, actual_range):
            violations.append("Plan x_range does not match user requested range.")

    expected_colors = requirements.get("requested_colors") or []
    if expected_colors and expected_equations:
        actual_colors = _extract_curve_colors_from_plan(plan)
        if actual_colors and not any(c in expected_colors for c in actual_colors):
            violations.append("Plan curve colors do not match requested color hints.")

    if requirements.get("high_confidence_trig_mapping"):
        scene_templates = {str(scene.template or "") for scene in (plan.scenes or [])}
        has_unit_circle = plan.template == "unit_circle" or "unit_circle" in scene_templates
        has_wave = (
            plan.template in {"trig_waves", "trig_comparison"}
            or "trig_waves" in scene_templates
            or "trig_comparison" in scene_templates
        )
        if not has_unit_circle:
            violations.append("Plan is missing unit-circle scene for trig mapping request.")
        if not has_wave:
            violations.append("Plan is missing waveform tracing/comparison scene.")

    return violations


def _build_requirement_locked_plot_plan(
    user_prompt: str, requirements: Dict[str, Any]
) -> Optional[AnimationPlan]:
    """Create deterministic draw_curve plan when prompt requests a single explicit equation."""
    if not requirements.get("single_curve_request"):
        return None

    equation = requirements.get("requested_equation")
    if not equation:
        return None

    plot_data: Dict[str, Any] = {"function": equation}
    x_range = requirements.get("requested_x_range")
    if isinstance(x_range, list) and len(x_range) == 2:
        plot_data["range"] = x_range

    requested_colors = requirements.get("requested_colors") or []
    if requested_colors:
        plot_data["color"] = requested_colors[0]

    return _build_plot_plan_from_structured(user_prompt, plot_data)


class _BSTNode:
    def __init__(self, value: int, idx: int) -> None:
        self.value = value
        self.idx = idx
        self.left: Optional["_BSTNode"] = None
        self.right: Optional["_BSTNode"] = None


def _bst_insert(root: Optional[_BSTNode], node: _BSTNode) -> _BSTNode:
    if root is None:
        return node
    if node.value < root.value:
        root.left = _bst_insert(root.left, node)
    else:
        root.right = _bst_insert(root.right, node)
    return root


def _extract_bst_values(user_prompt: str) -> List[int]:
    values: List[int] = []
    prompt = user_prompt or ""
    # Remove search-target phrases so the target is not treated as an insertion value.
    prompt = re.sub(
        r"\b(search|find)\s+(?:for\s+)?(?:value\s+)?-?\d+",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    for match in re.findall(r"-?\d+", prompt):
        try:
            values.append(int(match))
        except ValueError:
            continue
    return values


def _extract_bst_search_target(user_prompt: str) -> Optional[int]:
    if not user_prompt:
        return None
    match = re.search(r"search\s+for\s+value\s+(-?\d+)", user_prompt, re.IGNORECASE)
    if not match:
        match = re.search(r"find\s+value\s+(-?\d+)", user_prompt, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _build_requirement_locked_bst_plan(
    user_prompt: str, requirements: Dict[str, Any]
) -> Optional[AnimationPlan]:
    if not re.search(r"\b(bst|binary\s+search\s+tree)\b", user_prompt or "", re.IGNORECASE):
        return None

    values = _extract_bst_values(user_prompt)
    if not values:
        return None

    nodes: List[_BSTNode] = []
    root: Optional[_BSTNode] = None
    for idx, value in enumerate(values, start=1):
        node = _BSTNode(value=value, idx=idx)
        nodes.append(node)
        root = _bst_insert(root, node)

    positions: Dict[int, List[float]] = {}

    def _assign_positions(node: Optional[_BSTNode], x: float, y: float, dx: float) -> None:
        if node is None:
            return
        positions[node.idx] = [round(x, 2), round(y, 2), 0]
        next_dx = max(0.8, dx * 0.55)
        _assign_positions(node.left, x - dx, y - 1.5, next_dx)
        _assign_positions(node.right, x + dx, y - 1.5, next_dx)

    _assign_positions(root, 0.0, 1.5, 3.2)

    objects: List[AnimationObject] = [
        AnimationObject(
            id="bst_title",
            type="text",
            parameters={
                "text": "Binary Search Tree",
                "position": [0, 2.6, 0],
                "font_size": 38,
            },
        )
    ]

    edges: List[AnimationObject] = []
    node_objects: List[AnimationObject] = []
    for node in nodes:
        pos = positions.get(node.idx, [0, 0, 0])
        node_objects.append(
            AnimationObject(
                id=f"node_{node.idx}",
                type="node",
                parameters={"label": str(node.value), "position": pos},
            )
        )

    def _add_edge(parent: Optional[_BSTNode], child: Optional[_BSTNode]) -> None:
        if parent is None or child is None:
            return
        start = positions.get(parent.idx, [0, 0, 0])
        end = positions.get(child.idx, [0, 0, 0])
        edges.append(
            AnimationObject(
                id=f"edge_{parent.idx}_{child.idx}",
                type="line",
                parameters={"start": start, "end": end},
            )
        )

    for node in nodes:
        _add_edge(node, node.left)
        _add_edge(node, node.right)

    objects.extend(edges)
    objects.extend(node_objects)

    animations: List[AnimationStep] = [
        AnimationStep(object_id="bst_title", action="write", duration=1.2),
    ]
    for edge in edges:
        animations.append(AnimationStep(object_id=edge.id, action="create", duration=0.6))
    for node_obj in node_objects:
        animations.append(AnimationStep(object_id=node_obj.id, action="fade_in", duration=0.6))

    search_target = _extract_bst_search_target(user_prompt)
    if search_target is not None and root is not None:
        search_path: List[_BSTNode] = []
        current = root
        while current is not None:
            search_path.append(current)
            if search_target == current.value:
                break
            if search_target < current.value:
                current = current.left
            else:
                current = current.right

        for node in search_path:
            animations.append(
                AnimationStep(object_id=f"node_{node.idx}", action="highlight", duration=0.7)
            )
        last = search_path[-1]
        if search_target == last.value:
            animations.append(
                AnimationStep(
                    object_id=f"node_{last.idx}",
                    action="color",
                    parameters={"color": "GREEN"},
                    duration=0.8,
                )
            )

    style_hint = str(requirements.get("style_hint") or "3b1b")
    plan_title = "Binary Search Tree Visualization"
    return AnimationPlan(
        title=plan_title,
        style=style_hint,
        template=None,
        parameters={"values": values, "search_target": search_target},
        scenes=[
            AnimationScene(
                scene_id="bst_visualization",
                template="generic",
                objects=objects,
                animations=animations,
                narration=(
                    "Build the binary search tree from the given values, then trace the search path."
                ),
            )
        ],
    )


def _build_requirement_locked_solver_plan(
    user_prompt: str, requirements: Dict[str, Any]
) -> Optional[AnimationPlan]:
    """Create deterministic algebra-solving plan with optional graph scene."""
    requested_equation = _compact_prompt_text(
        str(
            requirements.get("requested_algebra_equation")
            or requirements.get("requested_equation")
            or ""
        )
    )
    if not requested_equation:
        return None

    if not (requirements.get("solve_request") or requirements.get("equation_graph_request")):
        return None

    solved = _derive_equation_solution(requested_equation)
    if not solved:
        return None

    steps_scene = _build_step_scene_from_lines(
        "equation_steps",
        "Solve the Equation",
        [str(s) for s in (solved.get("steps") or [])],
        "Solve the equation using ordered algebraic transformations.",
    )

    solution_lines = [f"Final solution: {solved.get('result', '')}"]
    real_roots = [float(v) for v in (solved.get("real_roots") or [])]
    if real_roots:
        roots_text = ", ".join(_format_numeric_for_calculation(v) for v in real_roots)
        solution_lines.append(f"Real roots / x-intercepts: {roots_text}")

    summary_scene = _build_step_scene_from_lines(
        "equation_solution",
        "Solution Summary",
        solution_lines,
        "Summarize the final solution and link it to the graph.",
    )

    include_graph = bool(
        requirements.get("plot_request")
        or re.search(r"\b(graph|plot|curve|visual)\b", user_prompt, re.IGNORECASE)
    )
    scenes: List[AnimationScene] = [steps_scene]
    if include_graph and solved.get("expression"):
        x_range = _pick_equation_plot_range(real_roots, requirements.get("requested_x_range"))
        expression = str(solved.get("expression") or "")
        y_range = _estimate_equation_y_range(expression, x_range)
        requested_colors = requirements.get("requested_colors") or []
        curve_color = _canonical_plot_color(requested_colors[0]) if requested_colors else "BLUE"

        graph_scene = AnimationScene(
            scene_id="equation_graph",
            template="draw_curve",
            depends_on=[steps_scene.scene_id],
            parameters={
                "expression": expression,
                "x_range": x_range,
                "y_range": y_range,
                "color": curve_color,
                "label": "f(x)",
            },
            narration=(
                "Plot f(x) after rewriting the equation as f(x)=0. "
                "The roots are where the curve crosses the x-axis."
            ),
        )
        scenes.append(graph_scene)
        summary_scene.depends_on = [graph_scene.scene_id]
    else:
        summary_scene.depends_on = [steps_scene.scene_id]

    scenes.append(summary_scene)
    return AnimationPlan(
        title="Equation Solving with Visual Graph",
        style=str(requirements.get("style_hint") or "3b1b"),
        template=None,
        parameters={
            "equation": solved.get("equation"),
            "expression": solved.get("expression"),
            "real_roots": real_roots,
        },
        scenes=scenes,
    )


def _build_requirement_locked_trig_plan(
    user_prompt: str, requirements: Dict[str, Any]
) -> Optional[AnimationPlan]:
    """Create deterministic unit-circle + waveform plan for high-confidence trig mapping prompts."""
    if not requirements.get("high_confidence_trig_mapping"):
        return None

    expected_equations = [
        _normalize_equation_for_compare(eq)
        for eq in (requirements.get("requested_equations") or [])
        if _normalize_equation_for_compare(eq)
    ]
    has_sin = any("np.sin" in eq for eq in expected_equations)
    has_cos = any("np.cos" in eq for eq in expected_equations)
    if not (has_sin and has_cos):
        return None

    requested_colors = list(requirements.get("requested_colors") or [])
    color_sin = requested_colors[0] if requested_colors else "GREEN"
    if len(requested_colors) >= 2 and requested_colors[1] != color_sin:
        color_cos = requested_colors[1]
    else:
        color_cos = "RED" if color_sin != "RED" else "BLUE"

    requested_range = requirements.get("requested_x_range")
    if isinstance(requested_range, list) and len(requested_range) == 2:
        x_range = requested_range
    else:
        x_range = [0.0, round(4.0 * math.pi, 4)]

    x_span = max(1.0, float(x_range[1]) - float(x_range[0]))
    x_step = round(max(x_span / 4.0, math.pi / 2.0), 4)

    title = "Unit Circle to Sine/Cosine Wave Mapping"
    style_hint = str(requirements.get("style_hint") or "3b1b")

    return AnimationPlan(
        title=title,
        style=style_hint,
        template=None,
        parameters={
            "focus": "unit_circle_wave_mapping",
            "x_range": x_range,
            "color_sin": color_sin,
            "color_cos": color_cos,
        },
        scenes=[
            AnimationScene(
                scene_id="unit_circle_setup",
                template="unit_circle",
                parameters={"color_sin": color_sin, "color_cos": color_cos, "run_time": 12},
                narration=(
                    "Start with a rotating radius on the unit circle and show sine and cosine "
                    "projection lines in distinct colors."
                ),
            ),
            AnimationScene(
                scene_id="waveform_mapping",
                template="trig_comparison",
                depends_on=["unit_circle_setup"],
                parameters={
                    "functions": ["sin", "cos"],
                    "colors": [color_sin, color_cos],
                    "x_range": [x_range[0], x_range[1], x_step],
                },
                narration=(
                    "Map the rotating angle to synchronized sine and cosine waveforms across "
                    "the requested domain."
                ),
            ),
            AnimationScene(
                scene_id="feature_labels",
                template="generic",
                depends_on=["waveform_mapping"],
                objects=[
                    AnimationObject(
                        id="feature_title",
                        type="text",
                        parameters={
                            "text": "Amplitude, Period, and Phase",
                            "position": [0, 2.2, 0],
                            "font_size": 34,
                        },
                    ),
                    AnimationObject(
                        id="amp_label",
                        type="math_tex",
                        parameters={
                            "text": r"Amplitude = 1",
                            "position": [-3.2, 0.9, 0],
                            "font_size": 30,
                        },
                    ),
                    AnimationObject(
                        id="period_label",
                        type="math_tex",
                        parameters={
                            "text": r"Period = 2\pi",
                            "position": [0, 0.9, 0],
                            "font_size": 30,
                        },
                    ),
                    AnimationObject(
                        id="phase_label",
                        type="math_tex",
                        parameters={
                            "text": r"Phase Shift = 0",
                            "position": [3.2, 0.9, 0],
                            "font_size": 30,
                        },
                    ),
                ],
                animations=[
                    AnimationStep(object_id="feature_title", action="write", duration=1.1),
                    AnimationStep(object_id="amp_label", action="fade_in", duration=1.0),
                    AnimationStep(object_id="period_label", action="fade_in", duration=1.0),
                    AnimationStep(object_id="phase_label", action="fade_in", duration=1.0),
                    AnimationStep(object_id="period_label", action="highlight", duration=0.9),
                ],
                narration=(
                    "Label the core waveform properties so the viewer can read amplitude, "
                    "period, and phase directly from the synchronized curves."
                ),
            ),
        ],
    )


def _build_requirement_locked_plan(
    user_prompt: str, requirements: Dict[str, Any]
) -> tuple[Optional[AnimationPlan], str]:
    bst_plan = _build_requirement_locked_bst_plan(user_prompt, requirements)
    if bst_plan is not None:
        return bst_plan, "bst_requirement_lock"

    solver_plan = _build_requirement_locked_solver_plan(user_prompt, requirements)
    if solver_plan is not None:
        return solver_plan, "solver_graph_requirement_lock"

    plot_plan = _build_requirement_locked_plot_plan(user_prompt, requirements)
    if plot_plan is not None:
        return plot_plan, "single_curve_requirement_lock"

    trig_plan = _build_requirement_locked_trig_plan(user_prompt, requirements)
    if trig_plan is not None:
        return trig_plan, "trig_mapping_requirement_lock"

    return None, ""


def _enforce_user_requirements_on_plan(
    plan: AnimationPlan, user_prompt: str, requirements: Dict[str, Any]
) -> AnimationPlan:
    """Apply deterministic corrections for explicit prompt constraints when possible."""
    if not requirements:
        return plan

    plan_copy = plan.model_copy(deep=True)
    style_hint = requirements.get("style_hint")
    if style_hint:
        plan_copy.style = str(style_hint)

    equation = requirements.get("requested_equation")
    expected_expr = _normalize_equation_for_compare(equation) if equation else ""
    expected_range = requirements.get("requested_x_range")
    expected_colors = requirements.get("requested_colors") or []

    if (
        expected_expr
        and isinstance(plan_copy.parameters, dict)
        and plan_copy.parameters.get("expression")
    ):
        plan_params = dict(plan_copy.parameters)
        plan_params["expression"] = expected_expr
        if isinstance(expected_range, list) and len(expected_range) == 2:
            plan_params["x_range"] = expected_range
        if expected_colors:
            plan_params["color"] = expected_colors[0]
        plan_copy.parameters = plan_params

    for scene in plan_copy.scenes or []:
        if scene.template != "draw_curve":
            continue
        scene_params = dict(scene.parameters or {})
        if expected_expr:
            scene_params["expression"] = expected_expr
        if isinstance(expected_range, list) and len(expected_range) == 2:
            scene_params["x_range"] = expected_range
        if expected_colors:
            scene_params["color"] = expected_colors[0]
        scene.parameters = scene_params

    return plan_copy


def _attempt_t5_structured_plan(user_prompt: str) -> tuple[Optional[AnimationPlan], Dict[str, Any]]:
    """Try to build a direct structured plan from strict T5 JSON output."""
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
        structured_prompt = T5_STRICT_MATH_JSON_PROMPT.replace("{user_input}", cleaned_prompt)
        if T5_STRUCTURED_TASK_PREFIX:
            structured_prompt = f"{T5_STRUCTURED_TASK_PREFIX}{structured_prompt}"

        inputs = tokenizer(
            structured_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=T5_MAX_INPUT_TOKENS,
        )

        generate_kwargs = {
            "max_length": T5_STRUCTURED_MAX_LENGTH,
            "temperature": T5_STRUCTURED_TEMPERATURE,
            "top_p": T5_STRUCTURED_TOP_P,
            "do_sample": False,
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

        normalized_payload = _normalize_t5_math_payload(cleaned_prompt, structured_data)
        if normalized_payload is None:
            # Backward compatibility with older graph-only structured output.
            legacy_plan = _build_plot_plan_from_structured(cleaned_prompt, structured_data)
            if legacy_plan is None:
                meta["reason"] = "invalid_schema"
                return None, meta

            legacy_params = dict(legacy_plan.parameters or {})
            legacy_params["structured_math_json"] = structured_data
            legacy_plan.parameters = legacy_params

            meta["used"] = True
            meta["reason"] = "legacy_graph_json"
            meta["structured_type"] = "trigonometry_graph"
            return legacy_plan, meta

        plan = _build_plan_from_t5_math_payload(cleaned_prompt, normalized_payload)
        if not plan:
            meta["reason"] = "unsupported_structured_output"
            return None, meta

        meta["used"] = True
        meta["reason"] = "ok"
        meta["structured_type"] = normalized_payload.get("type")
        meta["payload"] = normalized_payload
        meta["payload_preview"] = json.dumps(normalized_payload)[:240]
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

    requirements_preview = t5_meta.get("requirements")
    if requirements_preview:
        metadata["user_requirements"] = requirements_preview

    requirement_lock = t5_meta.get("requirement_lock")
    if requirement_lock:
        metadata["requirement_lock"] = requirement_lock

    raw_preview = structured_meta.get("raw_output")
    if raw_preview:
        metadata["structured_stage"]["raw_output_preview"] = raw_preview

    structured_type = structured_meta.get("structured_type")
    if structured_type:
        metadata["structured_stage"]["type"] = structured_type

    payload_preview = structured_meta.get("payload_preview")
    if payload_preview:
        metadata["structured_stage"]["payload_preview"] = payload_preview

    payload = structured_meta.get("payload")
    if isinstance(payload, dict):
        metadata["structured_stage"]["payload"] = payload

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

    # Keep template-free mode opt-in; do not implicitly enable it when routing is disabled.
    use_template_free_mode = False

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
    """Generate an animation plan with fresh planner inference on every request."""
    enhanced_prompt, t5_meta = _normalize_prompt_with_t5(user_prompt)
    prompt_for_planning = _merge_prompt_with_enhancement(user_prompt, enhanced_prompt)

    if t5_meta.get("applied"):
        logger.info("T5 enhanced prompt for planning")

    prompt_for_profile = user_prompt or enhanced_prompt or prompt_for_planning
    user_requirements = _extract_user_requirements(prompt_for_profile)
    requirements_brief = _format_user_requirements_for_planner(user_requirements)
    if requirements_brief:
        prompt_for_planning = (
            f"{prompt_for_planning}\n\n"
            "MANDATORY USER REQUIREMENTS (DO NOT DROP):\n"
            f"{requirements_brief}"
        )
    t5_meta["requirements"] = _requirements_preview_for_metadata(user_requirements)

    render_profile = _build_render_profile(prompt_for_profile)
    structured_seed_prompt = user_prompt or enhanced_prompt or prompt_for_planning
    _structured_plan, t5_struct_meta = _attempt_t5_structured_plan(structured_seed_prompt)

    def _profiled_fallback_plan(prompt_text: str) -> AnimationPlan:
        fallback_prompt = prompt_text or prompt_for_profile
        fallback_title = (fallback_prompt or "Concept Overview")[:60]
        fallback = _build_template_free_plan(fallback_prompt, "3b1b", fallback_title)
        fallback = _apply_render_profile_to_plan(fallback, render_profile, fallback_prompt)
        fallback = _attach_input_understanding_metadata(fallback, t5_meta, t5_struct_meta)
        return _finalize_plan_durations(fallback, render_profile)

    def _profiled_requirement_locked_plan() -> Optional[AnimationPlan]:
        """Build deterministic requirement-locked plans before generic fallback."""
        locked_plan, lock_reason = _build_requirement_locked_plan(
            prompt_for_profile, user_requirements
        )
        if locked_plan is None:
            return None

        t5_meta["requirement_lock"] = lock_reason
        locked_plan = _apply_render_profile_to_plan(locked_plan, render_profile, prompt_for_profile)
        locked_plan = _attach_input_understanding_metadata(locked_plan, t5_meta, t5_struct_meta)
        return _finalize_plan_durations(locked_plan, render_profile)

    if _structured_plan is not None:
        t5_struct_meta["used"] = True
        t5_struct_meta["reason"] = "structured_plan_applied"

        structured_plan = _apply_render_profile_to_plan(
            _structured_plan, render_profile, prompt_for_profile
        )
        structured_plan = _attach_input_understanding_metadata(
            structured_plan, t5_meta, t5_struct_meta
        )
        return _finalize_plan_durations(structured_plan, render_profile)

    if FORCE_FRESH_CODEGEN:
        deterministic_requirement_plan = _profiled_requirement_locked_plan()
        if deterministic_requirement_plan is not None:
            logger.info("FORCE_FRESH_CODEGEN enabled; using deterministic requirement-locked plan")
            return deterministic_requirement_plan

        logger.info(
            "FORCE_FRESH_CODEGEN enabled and no structured plan available; "
            "using template-free fallback instead of routed planner"
        )
        return _profiled_fallback_plan(prompt_for_profile)

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

    # guard against enormous prompts
    if len(prompt_for_planning) > 2000:
        logger.warning("Prompt too long; truncating to 2000 chars")
        prompt_for_planning = prompt_for_planning[:2000]

    t5_meta["planning_prompt_preview"] = prompt_for_planning[:280]

    try:
        plan = call_combined_llm_planner(prompt_for_planning, None)

        # Preserve explicit user constraints before validation.
        plan = _enforce_user_requirements_on_plan(plan, prompt_for_profile, user_requirements)

        # 4. Validate/repair plan unless validation checks are intentionally skipped.
        if not SKIP_PLAN_VALIDATION_CHECKS:
            violations = _validate_plan_against_user_requirements(plan, user_requirements)
            if violations:
                logger.warning(f"Plan violations detected: {violations}")
                plan = repair_plan(prompt_for_profile, None, plan, violations)
                plan = _enforce_user_requirements_on_plan(
                    plan, prompt_for_profile, user_requirements
                )

        # 4.5 Stabilize for unseen/complex prompts and sanitize unsafe scene references.
        plan = _stabilize_plan_for_rendering(plan, prompt_for_profile, None)

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


def _extract_python_code_block(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""

    fenced = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fenced:
        raw = fenced.group(1).strip()

    return raw


def _normalize_generated_manim_code(code: str) -> str:
    normalized = str(code or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return normalized

    if "from manim import *" not in normalized:
        normalized = "from manim import *\nimport numpy as np\n\n" + normalized
    elif "import numpy as np" not in normalized:
        normalized = normalized.replace("from manim import *", "from manim import *\nimport numpy as np", 1)

    class_match = re.search(r"class\s+(\w+)\s*\((Scene|GraphScene|ThreeDScene)\)\s*:", normalized)
    if class_match:
        class_name = class_match.group(1)
        base_cls = class_match.group(2)
        if class_name != "Scene1":
            normalized = re.sub(
                r"class\s+\w+\s*\((?:Scene|GraphScene|ThreeDScene)\)\s*:",
                f"class Scene1({base_cls}):",
                normalized,
                count=1,
            )

    if "class Scene1(" not in normalized or "def construct(self):" not in normalized:
        return ""

    return normalized + "\n"


def _detect_known_manim_codegen_issues(code: str) -> List[str]:
    issues: List[str] = []
    if not code:
        return issues

    if re.search(r"\.get_bar\s*\(", code):
        issues.append("Do not use axes.get_bar/get_bars; unsupported in Manim Community 0.19.")
    if re.search(r"\bShowCreation\s*\(", code):
        issues.append("Use Create(...) instead of ShowCreation(...).")
    if re.search(r"\bGraphScene\b", code):
        issues.append("Do not use legacy GraphScene; use Scene with Axes.")

    text_assignments = re.findall(r"^\s*([A-Za-z_]\w*)\s*=\s*(?:MathTex|Text)\s*\(", code, flags=re.MULTILINE)
    if len(text_assignments) >= 4:
        positioned = 0
        for name in text_assignments:
            if re.search(rf"\b{name}\s*\.(?:move_to|next_to|to_edge|to_corner|shift)\s*\(", code):
                positioned += 1

        has_text_cleanup = bool(
            re.search(r"\bFadeOut\s*\(", code)
            or re.search(r"\bReplacementTransform\s*\(", code)
            or re.search(r"\bTransformMatchingTex\s*\(", code)
        )

        if positioned < max(2, len(text_assignments) // 2):
            issues.append(
                "Sequential Text/MathTex steps must be explicitly positioned to avoid overlap."
            )
        if positioned < max(2, len(text_assignments) // 2) and not has_text_cleanup:
            issues.append(
                "Sequential Text/MathTex steps must be cleared or transformed; do not leave all steps on screen."
            )

    return issues


def _request_direct_manim_code(prompt_text: str) -> str:
    if LLM_PROVIDER == "openai":
        try:
            from openai import OpenAI

            kwargs: Dict[str, Any] = {"api_key": OPENAI_API_KEY or "sk-placeholder"}
            if OPENAI_BASE_URL:
                kwargs["base_url"] = OPENAI_BASE_URL
            client = OpenAI(**kwargs)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.2,
                max_tokens=2200,
                messages=[
                    {
                        "role": "system",
                        "content": "Return only Python Manim code.",
                    },
                    {
                        "role": "user",
                        "content": prompt_text,
                    },
                ],
            )
            content = response.choices[0].message.content or ""
            extracted = _extract_python_code_block(content)
            return _normalize_generated_manim_code(extracted)
        except Exception as exc:
            logger.error(f"OpenAI direct code generation failed: {exc}")
            return ""

    if LLM_PROVIDER == "gemini":
        try:
            model = get_gemini_model()
            response = model.generate_content(prompt_text)
            content = getattr(response, "text", "") or ""
            extracted = _extract_python_code_block(content)
            return _normalize_generated_manim_code(extracted)
        except Exception as exc:
            logger.error(f"Gemini direct code generation failed: {exc}")
            return ""

    logger.warning(f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}' for direct code generation")
    return ""


def _extract_evaluation_expression_from_prompt(user_prompt: str) -> str:
    prompt = _normalize_math_text(user_prompt or "")
    if not prompt:
        return ""

    match = re.search(
        r"\bevaluate\b\s*(.+?)(?=\s+\b(?:and|with|show|graph|plot|point|points|also)\b|[\.;]|$)",
        prompt,
        re.IGNORECASE,
    )
    if match:
        return _compact_prompt_text(match.group(1))

    return ""


def _safe_eval_math_expression(raw_expression: str) -> Optional[float]:
    expr = _normalize_math_text(raw_expression or "").lower()
    if not expr:
        return None

    expr = expr.replace("^", "**")
    expr = re.sub(r"(?<=\d)(?=[A-Za-z(])", "*", expr)
    expr = re.sub(r"(?<=\))(?=[A-Za-z0-9(])", "*", expr)

    replacements = {
        "sin": "math.sin",
        "cos": "math.cos",
        "tan": "math.tan",
        "sqrt": "math.sqrt",
        "log": "math.log",
        "exp": "math.exp",
    }
    for src, dst in replacements.items():
        expr = re.sub(rf"\b{src}\b", dst, expr)

    expr = re.sub(r"\btau\b", "(2*math.pi)", expr)
    expr = re.sub(r"\bpi\b", "math.pi", expr)

    if not re.fullmatch(r"[0-9A-Za-z_\+\-\*/\(\)\.,\s]*", expr):
        return None

    allowed_names = {"math", "sin", "cos", "tan", "sqrt", "log", "exp", "pi"}
    for token in re.findall(r"[A-Za-z_]+", expr):
        if token not in allowed_names:
            return None

    try:
        value = float(eval(expr, {"__builtins__": {}}, {"math": math}))  # nosec B307
        if math.isfinite(value):
            return value
    except Exception:
        return None

    return None


def _extract_trig_terms_for_points(expression: str) -> List[Dict[str, Any]]:
    expr = _normalize_math_text(expression or "").lower()
    expr = expr.replace("^", "**")
    expr = re.sub(r"\s+", "", expr)
    expr = re.sub(r"(?<=\d)(?=[A-Za-z(])", "*", expr)
    expr = re.sub(r"(?<=\))(?=[A-Za-z0-9(])", "*", expr)

    terms: List[Dict[str, Any]] = []
    for match in re.finditer(
        r"([+-]?(?:\d+(?:\.\d+)?|\.\d+)?)\*?(sin|cos)\(([^()]+)\)",
        expr,
    ):
        coeff_text, fn_name, angle_expr = match.groups()
        if coeff_text in {"", "+"}:
            coeff = 1.0
        elif coeff_text == "-":
            coeff = -1.0
        else:
            try:
                coeff = float(coeff_text)
            except ValueError:
                continue

        angle = _safe_eval_numeric_expression(angle_expr, float("nan"))
        if math.isnan(angle):
            continue

        base_y = math.sin(angle) if fn_name == "sin" else math.cos(angle)
        term_value = coeff * base_y
        terms.append(
            {
                "function": fn_name,
                "coefficient": coeff,
                "angle_expr": angle_expr,
                "angle": angle,
                "base_y": base_y,
                "term_value": term_value,
            }
        )

    return terms


def _build_direct_codegen_fallback(user_prompt: str) -> str:
    prompt_text = _compact_prompt_text(user_prompt or "")[:100]
    headline = prompt_text if prompt_text else "Animation"
    detail = prompt_text if prompt_text else "Generating a fresh visualization."

    normalized_prompt = _normalize_math_text(user_prompt or "")
    extracted_equation = _extract_equation_from_prompt(normalized_prompt)
    wants_graph = bool(re.search(r"\b(graph|plot|curve|visual)\b", normalized_prompt, re.IGNORECASE))
    solved = _derive_equation_solution(extracted_equation) if extracted_equation else None

    if solved:
        def _shorten_step(text: Any, max_len: int = 62) -> str:
            cleaned = _compact_prompt_text(str(text or ""))
            if len(cleaned) <= max_len:
                return cleaned
            return f"{cleaned[: max_len - 3]}..."

        coeffs = solved.get("coefficients") or {}
        a_val = float(coeffs.get("a", 0.0) or 0.0)
        b_val = float(coeffs.get("b", 0.0) or 0.0)
        c_val = float(coeffs.get("c", 0.0) or 0.0)

        steps: List[str] = []
        equation_line = _shorten_step(solved.get("equation") or extracted_equation)
        if equation_line:
            steps.append(equation_line)

        if abs(a_val) > 1e-10:
            steps.append(
                _shorten_step(
                    f"a={_format_numeric_for_calculation(a_val)}, "
                    f"b={_format_numeric_for_calculation(b_val)}, "
                    f"c={_format_numeric_for_calculation(c_val)}"
                )
            )
            delta_val = (b_val * b_val) - (4.0 * a_val * c_val)
            steps.append(_shorten_step(f"Delta = b^2 - 4ac = {_format_numeric_for_calculation(delta_val)}"))
            steps.append("x = (-b ± sqrt(Delta)) / (2a)")
        else:
            steps.append(
                _shorten_step(
                    f"Linear form: {_format_numeric_for_calculation(b_val)}x + "
                    f"{_format_numeric_for_calculation(c_val)} = 0"
                )
            )

        result_line = _shorten_step(f"Result: {solved.get('result', '')}")
        if result_line:
            steps.append(result_line)

        steps_literal = json.dumps(steps, ensure_ascii=True)
        expression = str(solved.get("expression") or "x")
        real_roots = [float(v) for v in (solved.get("real_roots") or [])]
        roots_literal = json.dumps(real_roots)

        x_range = _pick_equation_plot_range(real_roots, None)
        y_range = _estimate_equation_y_range(expression, x_range)

        code_parts: List[str] = [
            "from manim import *",
            "import numpy as np",
            "",
            "config.background_color = '#0a0a0f'",
            "config.frame_rate = 30",
            "",
            "class Scene1(Scene):",
            "    def construct(self):",
            "        title = Text('Solve Equation Step-by-Step', font_size=34).to_edge(UP)",
            "        self.play(Write(title))",
            f"        steps = {steps_literal}",
            "        step_mob = Text(steps[0], font_size=30).next_to(title, DOWN, buff=0.5)",
            "        self.play(FadeIn(step_mob), run_time=0.8)",
            "        self.wait(0.4)",
            "        for line in steps[1:]:",
            "            next_step = Text(line, font_size=30).move_to(step_mob)",
            "            self.play(ReplacementTransform(step_mob, next_step), run_time=0.9)",
            "            step_mob = next_step",
            "            self.wait(0.35)",
        ]

        if wants_graph:
            code_parts.extend(
                [
                    "        self.play(step_mob.animate.to_corner(UL).scale(0.62), run_time=0.8)",
                    "        axes = Axes(",
                    f"            x_range=[{x_range[0]}, {x_range[1]}, 1],",
                    f"            y_range=[{y_range[0]}, {y_range[1]}, 1],",
                    "            x_length=8,",
                    "            y_length=5,",
                    "            axis_config={'include_tip': False},",
                    "        ).to_edge(DOWN)",
                    f"        graph = axes.plot(lambda x: {expression}, x_range=[{x_range[0]}, {x_range[1]}], color=BLUE)",
                    "        self.play(Create(axes), run_time=1.0)",
                    "        self.play(Create(graph), run_time=1.2)",
                    f"        roots = {roots_literal}",
                    "        for root in roots:",
                    "            dot = Dot(axes.c2p(root, 0), color=RED)",
                    "            label = MathTex(rf'x={root:g}').scale(0.6).next_to(dot, UP, buff=0.12)",
                    "            self.play(FadeIn(dot), Write(label), run_time=0.55)",
                ]
            )

        final_result = _compact_prompt_text(str(solved.get("result") or "Solution obtained"))
        code_parts.extend(
            [
                f"        solution = Text({final_result!r}, font_size=30, color=YELLOW).to_edge(DOWN)",
                "        self.play(FadeIn(solution), run_time=0.9)",
                "        self.wait(1.6)",
            ]
        )

        return "\n".join(code_parts) + "\n"

    evaluation_expression = _extract_evaluation_expression_from_prompt(normalized_prompt)
    if evaluation_expression:
        evaluated_value = _safe_eval_math_expression(evaluation_expression)
        trig_terms = _extract_trig_terms_for_points(evaluation_expression)

        if evaluated_value is not None:
            step_lines: List[str] = [
                f"Expression: {evaluation_expression}",
            ]
            for idx, term in enumerate(trig_terms, start=1):
                coeff = _format_numeric_for_calculation(term.get("coefficient"))
                fn_name = str(term.get("function") or "sin")
                angle_expr = str(term.get("angle_expr") or "0")
                base_y = _format_numeric_for_calculation(term.get("base_y"))
                term_value = _format_numeric_for_calculation(term.get("term_value"))
                step_lines.append(
                    f"Term {idx}: {coeff}*{fn_name}({angle_expr}) = {coeff}*{base_y} = {term_value}"
                )
            step_lines.append(
                f"Final value: {_format_numeric_for_calculation(evaluated_value)}"
            )

            lines_literal = json.dumps(step_lines, ensure_ascii=True)
            result_text = _format_numeric_for_calculation(evaluated_value)
            has_sin = any(str(t.get("function")) == "sin" for t in trig_terms)
            has_cos = any(str(t.get("function")) == "cos" for t in trig_terms)

            code_parts: List[str] = [
                "from manim import *",
                "import numpy as np",
                "",
                "config.background_color = '#0a0a0f'",
                "config.frame_rate = 30",
                "",
                "class Scene1(Scene):",
                "    def construct(self):",
                "        title = Text('Evaluate Expression', font_size=34).to_edge(UP)",
                "        self.play(Write(title))",
                f"        steps = {lines_literal}",
                "        step_mob = Text(steps[0], font_size=28).next_to(title, DOWN, buff=0.4)",
                "        self.play(FadeIn(step_mob), run_time=0.8)",
                "        self.wait(0.35)",
                "        for line in steps[1:]:",
                "            next_step = Text(line, font_size=26).move_to(step_mob)",
                "            self.play(ReplacementTransform(step_mob, next_step), run_time=0.85)",
                "            step_mob = next_step",
                "            self.wait(0.3)",
            ]

            if wants_graph and trig_terms:
                code_parts.extend(
                    [
                        "        self.play(step_mob.animate.to_corner(UL).scale(0.58), run_time=0.7)",
                        "        axes = Axes(",
                        "            x_range=[-2*np.pi, 2*np.pi, np.pi/2],",
                        "            y_range=[-1.6, 1.6, 0.4],",
                        "            x_length=8.5,",
                        "            y_length=4.6,",
                        "            axis_config={'include_tip': False},",
                        "        ).to_edge(DOWN)",
                        "        self.play(Create(axes), run_time=1.0)",
                    ]
                )

                if has_sin:
                    code_parts.append(
                        "        sin_curve = axes.plot(lambda x: np.sin(x), x_range=[-2*np.pi, 2*np.pi], color=GREEN)"
                    )
                    code_parts.append("        self.play(Create(sin_curve), run_time=1.0)")
                if has_cos:
                    code_parts.append(
                        "        cos_curve = axes.plot(lambda x: np.cos(x), x_range=[-2*np.pi, 2*np.pi], color=BLUE)"
                    )
                    code_parts.append("        self.play(Create(cos_curve), run_time=1.0)")

                terms_literal = json.dumps(trig_terms)
                code_parts.extend(
                    [
                        f"        trig_terms = {terms_literal}",
                        "        for term in trig_terms:",
                        "            x_val = float(term['angle'])",
                        "            y_val = float(term['base_y'])",
                        "            dot_color = GREEN if term['function'] == 'sin' else BLUE",
                        "            dot = Dot(axes.c2p(x_val, y_val), color=dot_color)",
                        "            lbl = Text(f\"{term['function']}({term['angle_expr']})={y_val:.2f}\", font_size=20).next_to(dot, UP, buff=0.12)",
                        "            self.play(FadeIn(dot), FadeIn(lbl), run_time=0.55)",
                    ]
                )

            code_parts.extend(
                [
                    f"        result = Text('Result = {result_text}', font_size=30, color=YELLOW).to_edge(DOWN)",
                    "        self.play(FadeIn(result), run_time=0.9)",
                    "        self.wait(1.8)",
                ]
            )

            return "\n".join(code_parts) + "\n"

    return (
        "from manim import *\n"
        "import numpy as np\n\n"
        "config.background_color = '#0a0a0f'\n"
        "config.frame_rate = 30\n\n"
        "class Scene1(Scene):\n"
        "    def construct(self):\n"
        f"        title = Text({headline!r}, font_size=32).to_edge(UP)\n"
        f"        detail = Text({detail!r}, font_size=24).next_to(title, DOWN, buff=0.6)\n"
        "        self.play(Write(title))\n"
        "        self.play(FadeIn(detail))\n"
        "        self.wait(2)\n"
    )


def _generate_manim_code_direct(user_prompt: str, plan: Optional[AnimationPlan] = None) -> str:
    cleaned_prompt = _compact_prompt_text(user_prompt or "")
    plan_hint = ""
    if isinstance(plan, AnimationPlan):
        try:
            plan_hint = plan.model_dump_json()
        except Exception:
            plan_hint = ""
    plan_hint = plan_hint[:8000]

    direct_codegen_prompt = (
        "You are an expert Manim code generator. Return ONLY executable Python code.\n"
        "Rules:\n"
        "1. Use 'from manim import *' and 'import numpy as np'.\n"
        "2. Define exactly one class Scene1(Scene) with construct(self).\n"
        "3. Do not output markdown fences, JSON, or commentary.\n"
        "4. Do not use undefined variables.\n"
        "5. If user asks for solve/evaluate, show visual step-by-step text or MathTex transforms.\n"
        "6. If user asks for graph/plot/points, include Axes and plotted curve/points.\n"
        "7. Keep text concise to avoid overflow.\n"
        "8. Use only Manim Community v0.19-safe APIs.\n"
        "9. For bar visuals, use BarChart(...) or Rectangle bars; NEVER use axes.get_bar/get_bars.\n"
        "10. For step-by-step explanations, avoid overlapping text: either position steps at different y-levels or reuse a single step object with ReplacementTransform/TransformMatchingTex.\n"
        "11. When introducing a new long step, fade out or transform older step text so the screen stays readable.\n"
        "12. Generate new code from this specific input; do not reuse canned scenes.\n\n"
        f"USER INPUT:\n{cleaned_prompt}\n\n"
        f"OPTIONAL PLAN HINT (can be ignored if low quality):\n{plan_hint}\n"
    )

    first_attempt = _request_direct_manim_code(direct_codegen_prompt)
    if first_attempt:
        issues = _detect_known_manim_codegen_issues(first_attempt)
        if not issues:
            return first_attempt

        retry_prompt = (
            f"{direct_codegen_prompt}\n"
            "CRITICAL COMPATIBILITY FIXES NEEDED:\n"
            + "\n".join(f"- {issue}" for issue in issues)
            + "\n\nPREVIOUS INVALID CODE (DO NOT REPEAT THESE ISSUES):\n"
            + first_attempt
            + "\n\nReturn a full corrected script now."
        )
        second_attempt = _request_direct_manim_code(retry_prompt)
        if second_attempt and not _detect_known_manim_codegen_issues(second_attempt):
            return second_attempt

    return _build_direct_codegen_fallback(cleaned_prompt)


def generate_manim_code(user_prompt: str, plan: Optional[AnimationPlan] = None) -> str:
    """Generate fresh Manim code directly from user input (template-free path)."""
    working_plan = plan
    if working_plan is None:
        try:
            working_plan = generate_plan(user_prompt)
        except Exception as exc:
            logger.error(f"Plan generation failed before direct codegen: {exc}")
            working_plan = None

    return _generate_manim_code_direct(user_prompt, working_plan)


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
    if re.search(r"\bunit[\s\-]?circle\b", p):
        return UserIntent(concept="trigonometry", template="unit_circle")

    has_trig_terms = bool(re.search(r"\b(trig|trigonometry|sin|sine|cos|cosine)\b", p))
    has_graph_terms = bool(
        re.search(r"\b(graph|plot|curve|wave|amplitude|frequency|period|phase)\b", p)
    )
    if has_trig_terms and has_graph_terms:
        return UserIntent(concept="trigonometry_graph", template="trig_waves")
    if has_trig_terms:
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
