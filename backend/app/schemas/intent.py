from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


Domain = Literal["calculus", "linear_algebra", "algorithms", "ml", "trigonometry", "general"]
Difficulty = Literal["beginner", "intermediate", "advanced"]


class ConceptExtraction(BaseModel):
    """Rich structured concept extracted from user prompt by Stage 1 LLM."""

    concept: str = Field(..., description="Primary mathematical or algorithmic concept")
    domain: Domain = Field(default="general", description="Academic domain of the concept")
    difficulty: Difficulty = Field(default="intermediate", description="Estimated difficulty level")
    sub_topics: List[str] = Field(
        default_factory=list,
        description="Supporting concepts relevant to the main concept (max 5)",
    )
    visual_goal: str = Field(
        default="",
        description="What should be visually understood after watching the animation",
    )
    # Optional routing hint (filled in Stage 2)
    template: Optional[str] = Field(None, description="Matched template name from capability registry")


class UserIntent(BaseModel):
    """Legacy intent schema — kept for backward compatibility with router code."""

    concept: str = Field(..., description="The core mathematical or algorithmic concept")
    template: Optional[str] = Field(None, description="The matched template name if any")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters for the template")
    notes: str = Field(default="", description="Brief context for debugging")
