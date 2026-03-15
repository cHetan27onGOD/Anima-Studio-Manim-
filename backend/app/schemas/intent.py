from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class UserIntent(BaseModel):
    """Extracted user intent from animation prompt."""
    
    concept: str = Field(..., description="The core mathematical or algorithmic concept")
    template: Optional[str] = Field(None, description="The matched template name if any")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters for the template")
    notes: str = Field(default="", description="Brief context for debugging")
