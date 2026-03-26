#!/usr/bin/env python
"""Simple test to validate the animation pipeline flow."""

import os
import sys

# Set minimal env vars for testing
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GEMINI_API_KEY", "test-key-123")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

from app.schemas.animation import AnimationPlan
from app.services.llm import (
    rule_based_concept_router,
    generate_plan,
)
from app.templates.capabilities import initialize_all_capabilities, get_capability_registry

def test_router():
    """Test concept router for known and unknown prompts."""
    print("=" * 60)
    print("TEST 1: Rule-Based Concept Router")
    print("=" * 60)
    
    test_cases = [
        ("Explain matrix multiplication", "matrix_multiplication"),
        ("How does MNIST work?", "mnist"),
        ("Visualize gradient descent", "gradient_descent"),
        ("Show me eigenvectors", "eigenvectors"),
        ("Unknown topic about flying dragons", None),
    ]
    
    for prompt, expected_concept in test_cases:
        intent = rule_based_concept_router(prompt)
        if intent:
            print(f"✓ '{prompt}' -> concept='{intent.concept}', template='{intent.template}'")
            if expected_concept and intent.concept != expected_concept:
                print(f"  WARNING: Expected concept={expected_concept}, got {intent.concept}")
        else:
            print(f"✗ '{prompt}' -> No match (router returned None)")
            if expected_concept:
                print(f"  WARNING: Expected concept={expected_concept}")
    print()

def test_capabilities():
    """Test that capability registry is properly initialized."""
    print("=" * 60)
    print("TEST 2: Capability Registry")
    print("=" * 60)
    
    initialize_all_capabilities()
    registry = get_capability_registry()
    
    # Test if registry has templates
    if registry.registry:
        print(f"✓ Registry initialized with {len(registry.registry)} template capabilities")
        # Show a few examples
        sample_concepts = list(registry.registry.keys())[:5]
        for concept in sample_concepts:
            print(f"  - {concept}")
    else:
        print("✗ Registry is empty!")
    print()

def test_plan_generation_without_llm():
    """Test fallback plan generation when LLM is unavailable."""
    print("=" * 60)
    print("TEST 3: Fallback Plan Generation (No Real LLM)")
    print("=" * 60)
    
    # Mock the LLM call to avoid requiring real API
    import app.services.llm as llm_module
    
    # Since generate_plan will try to call Redis and LLM, we'll just check if the fallback works
    prompts = [
        "Explain linear algebra",
        "Matrix multiplication step by step",
        "MNIST digit recognition",
    ]
    
    for prompt in prompts:
        try:
            # This will use cached/fallback since we have no real LLM configured
            plan = generate_plan(prompt)
            if isinstance(plan, AnimationPlan):
                print(f"✓ '{prompt}' -> Generated plan with {len(plan.scenes)} scenes")
                print(f"  Title: {plan.title}")
                if plan.scenes:
                    print(f"  First scene template: {plan.scenes[0].template}")
            else:
                print(f"✗ '{prompt}' -> Unexpected result type: {type(plan)}")
        except Exception as e:
            print(f"✗ '{prompt}' -> ERROR: {str(e)[:80]}")
    print()

if __name__ == "__main__":
    try:
        test_router()
        test_capabilities()
        test_plan_generation_without_llm()
        print("=" * 60)
        print("SUMMARY: Tests completed. See output above for details.")
        print("=" * 60)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
