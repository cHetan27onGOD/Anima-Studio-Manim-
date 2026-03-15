"""LLM service for generating animation plans using Google Gemini with intent validation."""

import json
import logging
import os
import re
import hashlib
from typing import Any, Optional, Dict

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
import redis
from pydantic import ValidationError

from app.schemas.animation import AnimationPlan
from app.schemas.intent import UserIntent
from app.core.config import settings
from app.templates.engine import TEMPLATES as AVAILABLE_TEMPLATES
from app.templates.capabilities import get_capability_registry
from app.services.narration import NarrationPipeline

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

LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
- eigenvectors_advanced: Shows linear transformation, scaling, and the stable direction of eigenvectors.
- vector_projection: Geometric projection of vectors with dashed lines.
- derivative_slope: Visualizes the tangent line approaching the derivative (f'(x)).
- integral_accumulation: Visualizes Riemann sums and area under curve (∫f(x)dx).
- polynomial_factoring: Visualizes algebraic splitting of polynomials using area models.
- unit_circle: Visualizes sin/cos projections on a rotating unit circle.
- trig_waves: Generates sine/cosine waves from a rotating unit circle.
- sorting: Visualizes sorting algorithms (like bubble sort) using bars.
- dijkstra: Visualizes shortest path in a weighted graph.
- projectile_motion: (Compose: draw_axis + draw_curve + place_point) Parabolic motion with gravity.

SCENE GRAPH COMPOSITION:
- Break the explanation into 3-6 distinct scenes.
- Use 'depends_on' to maintain state across scenes.
- Use 'templates' list to combine multiple micro-actions.

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
- FOR TRIGONOMETRY: Always use 'unit_circle' to explain sine/cosine fundamentally.
- FOR EIGENVECTORS: Use 'eigenvector' (basic) or 'eigenvectors_advanced' (for equations Av=λv).
- FOR ALGEBRA: Use 'polynomial_factoring' for equations or 'generic' with 'write_text' for derivations.
- FOR CALCULUS: Use 'derivative_slope' for tangents or 'integral_accumulation' for areas.
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


def refine_plan(original_prompt: str, original_plan: AnimationPlan, refinement_prompt: str) -> AnimationPlan:
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
    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set, using fallback plan")
            return AnimationPlan.create_fallback(user_prompt)
    elif LLM_PROVIDER == "openai":
        if not (OPENAI_API_KEY or OPENAI_BASE_URL):
            logger.warning("OPENAI configuration missing, using fallback plan")
            return AnimationPlan.create_fallback(user_prompt)
    else:
        logger.warning(f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}', using fallback plan")
        return AnimationPlan.create_fallback(user_prompt)

    # 1. Check Redis Cache
    cache_key = f"plan_v2:{hashlib.md5(user_prompt.encode()).hexdigest()}"
    try:
        cached_plan = redis_client.get(cache_key)
        if cached_plan:
            logger.info("Plan found in cache", extra={"prompt": user_prompt[:50]})
            return AnimationPlan.model_validate_json(cached_plan)
    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")

    # 2. Concept Router (Lightweight check before LLM)
    concept_intent = rule_based_concept_router(user_prompt)

    # guard against enormous prompts
    if len(user_prompt) > 2000:
        logger.warning("Prompt too long; truncating to 2000 chars")
        user_prompt = user_prompt[:2000]

    try:
        plan = call_combined_llm_planner(user_prompt, concept_intent)

        # Force template if detected by router but not set by LLM
        if concept_intent and concept_intent.template and not plan.template:
            plan.template = concept_intent.template

        # 4. Validate Plan
        violations = validate_plan_against_intent(plan, concept_intent, user_prompt)
        if violations:
            logger.warning(f"Plan violations detected: {violations}")
            plan = repair_plan(user_prompt, concept_intent, plan, violations)

        # 5. Post-process narration and durations in plan (Phase 3)
        try:
            pipeline = NarrationPipeline()
            plan = pipeline.process_plan(plan)
        except Exception as ex:
            logger.warning(f"Narration pipeline post-processing failed: {ex}")

        # 6. Cache result
        try:
            redis_client.setex(cache_key, 3600 * 24, plan.model_dump_json())
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")

        logger.info("plan_generated", extra={
            "template": plan.template,
            "title": plan.title,
            "scenes": len(plan.parameters.get("scenes", [])) if plan.template == "generic" else 1
        })
        return plan

    except LLMQuotaExceededError as e:
        logger.error(f"LLM quota exceeded: {e}")
        # return a minimal fallback that instructs the user to simplify
        return AnimationPlan.create_rate_limited_fallback(user_prompt)
    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        return AnimationPlan.create_fallback(user_prompt)

def generate_manim_code(user_prompt: str) -> str:
    """
    Generate Manim Python code from user prompt.
    """
    # 1. Generate the plan (uses caching, combined LLM call, and validation)
    plan = generate_plan(user_prompt)
    
    # 2. Convert plan to code using the template engine
    from app.worker.tasks import generate_manim_code_from_plan
    return generate_manim_code_from_plan(plan)

def rule_based_concept_router(prompt: str) -> Optional[UserIntent]:
    """
    Lightweight concept detection for routing to appropriate Phase 1/2 templates.
    Returns a hint for the LLM planner.
    """
    p = prompt.lower()
    
    # Linear Algebra concepts
    if "eigenvector" in p or "eigenvalue" in p:
        return UserIntent(concept="eigenvectors", template="eigenvectors_advanced")
    if "projection" in p and "vector" in p:
        return UserIntent(concept="vector_projection", template="vector_projection")
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
        return UserIntent(concept="embeddings", template="embedding_spaces")
    if "convolution" in p or "filter" in p and "cnn" in p:
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
        return UserIntent(concept="algebra_factoring", template="polynomial_factoring")
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
        "\n\nNOTE: Please produce no more than 8 scenes and keep the total plan "
        "size under 2000 tokens. Be concise and avoid extraneous detail."
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
            if 'quota' in msg.lower() or 'limit' in msg.lower() or '429' in msg:
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

    # Validate scenes
    scenes = plan.parameters.get("scenes", [])
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
    user_prompt: str,
    intent: Optional[UserIntent],
    plan: AnimationPlan,
    violations: list[str]
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
