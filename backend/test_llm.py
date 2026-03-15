import os
import pytest

from app.schemas.animation import AnimationPlan
from app.services.llm import (
    generate_plan,
    rule_based_concept_router,
    LLMQuotaExceededError,
    LLM_PROVIDER,
)
from app.services.narration import NarrationPipeline


def test_generate_plan_with_missing_gemini_key_falls_back(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', '')
    plan = generate_plan('Explain eigenvectors')
    assert isinstance(plan, AnimationPlan)
    assert plan.title
    assert plan.rate_limited is False


def test_generate_plan_with_openai_fallback(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('OPENAI_BASE_URL', '')
    plan = generate_plan('Explain vectors')
    assert isinstance(plan, AnimationPlan)
    assert plan.title


def test_router_capability_fallback_for_unknown_prompt(monkeypatch):
    # Capabilities registry is initialized in app startup; ensure it exists
    from app.templates.capabilities import initialize_all_capabilities
    initialize_all_capabilities()

    intent = rule_based_concept_router('Explain eigenvectors in a 2D transform')
    assert intent is not None
    assert intent.template is not None


def test_narration_pipeline_fills_missing(monkeypatch):
    p = AnimationPlan(
        title='Test',
        scenes=[
            {
                'scene_id': 'demo1',
                'description': 'Demo scene',
                'template': 'generic',
                'narration': None,
                'duration': 0.0,
            }
        ],
    )
    pipeline = NarrationPipeline()
    plan_out = pipeline.process_plan(p)
    assert plan_out.scenes[0].narration is not None
    assert plan_out.calculate_total_duration() > 0
