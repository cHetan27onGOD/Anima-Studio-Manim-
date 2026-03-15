from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

class ObjectLifecycle(Enum):
    CREATED = "created"
    VISIBLE = "visible"
    TRANSFORMED = "transformed"
    HIDDEN = "hidden"
    DESTROYED = "destroyed"

@dataclass
class CompositionObject:
    object_id: str
    object_type: str
    creation_code: str
    state: ObjectLifecycle = ObjectLifecycle.CREATED
    data: Dict[str, Any] = field(default_factory=dict)

class CompositionContext:
    def __init__(self, scene_id: str):
        self.scene_id = scene_id
        self.objs = {}
        self.stack = []
        self.order = []
        self.pre = ""
        self.post = ""

    def _namespace(self, logical_id: str) -> str:
        """Convert logical ID to internal namespaced ID."""
        return f"{self.scene_id}_{logical_id}"
    
    def add_obj(self, lid: str, otype: str, code: str, data: Optional[Dict[str, Any]] = None):
        nid = self._namespace(lid)
        if nid not in self.objs:
            self.objs[nid] = CompositionObject(nid, otype, code, data=data or {})
            self.order.append(nid)

    def add_object(self, logical_id: str, obj_type: str, creation_code: str, data: Optional[Dict[str, Any]] = None):
        """Alias for add_obj for documentation compatibility."""
        self.add_obj(logical_id, obj_type, creation_code, data)
    
    def add_anim(self, code: str):
        if code not in self.stack:
            self.stack.append(code)

    def add_animation_code(self, code: str):
        """Alias for add_anim for documentation compatibility."""
        self.add_anim(code)
            
    def object_exists(self, lid: str) -> bool:
        return self._namespace(lid) in self.objs

    def get_object(self, lid: str) -> Optional[CompositionObject]:
        return self.objs.get(self._namespace(lid))

    def get_available_objects(self) -> List[str]:
        # Return logical IDs (without namespace)
        prefix = f"{self.scene_id}_"
        return [nid[len(prefix):] for nid in self.objs.keys()]

    def finalize(self) -> str:
        res = [self.pre, "        # --- Objects ---\n"]
        for nid in self.order:
            o = self.objs[nid]
            res.append(f"        # {nid}: {o.object_type}\n")
            res.append(o.creation_code)
        res.append("\n        # --- Animations ---\n")
        res.extend(self.stack)
        res.append(self.post)
        return "".join(res)

class TemplateComposer:
    def __init__(self, scene_id: str):
        self.context = CompositionContext(scene_id)
        self.templates = []
    
    def add_template(self, template):
        self.templates.append(template)
    
    def compose(self) -> str:
        self.context.pre = "        # Scene initialization\n"
        for t in self.templates:
            t.compose_with_context(self.context)
        return self.context.finalize()

from app.templates.base import BaseTemplate

class CompositionAwareTemplate(BaseTemplate):
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.context: Optional[CompositionContext] = None

    def generate_construct_code(self) -> str:
        c = TemplateComposer(str(uuid.uuid4())[:8])
        c.add_template(self)
        return c.compose()
    
    def compose_with_context(self, context: CompositionContext):
        self.context = context
        self.compose(context)
        
    def compose(self, context: CompositionContext):
        raise NotImplementedError()

    # Helper methods that proxy to context for documentation compatibility
    def object_exists(self, logical_id: str) -> bool:
        if self.context:
            return self.context.object_exists(logical_id)
        return False

    def create_object(self, logical_id: str, obj_type: str, creation_code: str, data: Optional[Dict[str, Any]] = None):
        if self.context:
            self.context.add_object(logical_id, obj_type, creation_code, data)

    def add_animation_code(self, code: str):
        if self.context:
            self.context.add_animation_code(code)

    def get_available_objects(self) -> List[str]:
        if self.context:
            return self.context.get_available_objects()
        return []

    def get_object(self, logical_id: str) -> Optional[CompositionObject]:
        if self.context:
            return self.context.get_object(logical_id)
        return None
