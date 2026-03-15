from typing import Set, Dict, List, Type, Optional
from dataclasses import dataclass, field
import logging
logger = logging.getLogger(__name__)

@dataclass
class TemplateCapabilities:
    template_id: str
    name: str
    description: str
    concepts: Set[str] = field(default_factory=set)
    composition_ready: bool = False
    estimated_duration: float = 5.0
    def matches_concept(self, concept: str) -> float:
        if concept.lower() in [c.lower() for c in self.concepts]: return 1.0
        for c in self.concepts:
            if concept.lower() in c.lower() or c.lower() in concept.lower(): return 0.7
        return 0.0

class CapabilityRegistry:
    def __init__(self): self.registry = {}
    def register(self, caps): self.registry[caps.template_id] = caps
    def find_templates_for_concept(self, concept, composition_mode=False):
        matches = []
        for tid, caps in self.registry.items():
            if composition_mode and not caps.composition_ready: continue
            score = caps.matches_concept(concept)
            if score > 0: matches.append((tid, score))
        matches.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches]
    def get_capabilities(self, tid): return self.registry.get(tid)

_registry = CapabilityRegistry()
def get_capability_registry(): return _registry
def register_template_capabilities(tid, concepts, composition_ready=False, duration=5.0, name="", description=""):
    get_capability_registry().register(TemplateCapabilities(tid, name or tid.title(), description, concepts, composition_ready, duration))

def initialize_all_capabilities():
    register_template_capabilities("unit_circle", {"unit circle"}, True, 8.0, description="Params: color_cos, color_sin, run_time.")
    register_template_capabilities("trig_waves", {"waves"}, True, 6.0, description="Params: expression, color, run_time.")
    register_template_capabilities("draw_curve", {"curve", "comparison"}, True, 2.0, description="To compare, use MULTIPLE draw_curve instances with UNIQUE object_ids. Params: expression, color, label, object_id.")
    register_template_capabilities("draw_axis", {"axes"}, True, 2.0)
    register_template_capabilities("write_text", {"text"}, True, 2.0)
