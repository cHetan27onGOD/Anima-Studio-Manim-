"""Scene Composition Framework for stateful multi-template rendering."""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ObjectLifecycle(Enum):
    """Track object visibility and state through the composition."""
    CREATED = "created"
    VISIBLE = "visible"
    TRANSFORMED = "transformed"
    HIDDEN = "hidden"
    DESTROYED = "destroyed"

@dataclass
class CompositionObject:
    """Represents an object in the composition with state tracking."""
    object_id: str
    object_type: str
    creation_code: str  # Code that creates this object
    state: ObjectLifecycle = ObjectLifecycle.CREATED
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.object_id)

@dataclass
class CompositionContext:
    """
    Manages objects and state across composed templates with namespace isolation.
    
    Objects are namespaced by scene_id to prevent collisions:
    - Internal ID: "scene1_vector"
    - Logical reference: "vector"
    """
    scene_id: str
    objects: Dict[str, CompositionObject] = field(default_factory=dict)  # Uses namespaced IDs
    code_stack: List[str] = field(default_factory=list)  # Stack of code snippets with order
    object_order: List[str] = field(default_factory=list)  # Topological order for dependencies
    preamble: str = ""  # Code that runs before all templates
    postamble: str = ""  # Code that runs after all templates
    
    def _namespace(self, logical_id: str) -> str:
        """Convert logical object ID to namespaced ID."""
        return f"{self.scene_id}_{logical_id}"
    
    def add_object(self, logical_id: str, obj_type: str, creation_code: str, 
                   data: Optional[Dict[str, Any]] = None) -> None:
        """
        Register an object in the composition with automatic namespacing.
        
        Args:
            logical_id: Logical name (e.g., "vector")
            obj_type: Object type
            creation_code: Manim code
            data: Metadata
        """
        namespaced_id = self._namespace(logical_id)
        obj = CompositionObject(
            object_id=namespaced_id,
            object_type=obj_type,
            creation_code=creation_code,
            data=data or {}
        )
        
        if namespaced_id in self.objects:
            logger.warning(f"Object {namespaced_id} already exists, overwriting")
        
        self.objects[namespaced_id] = obj
        if namespaced_id not in self.object_order:
            self.object_order.append(namespaced_id)
    
    def get_object(self, logical_id: str) -> Optional[CompositionObject]:
        """
        Retrieve object by logical ID (uses namespacing internally).
        """
        namespaced_id = self._namespace(logical_id)
        return self.objects.get(namespaced_id)
    
    def object_exists(self, logical_id: str) -> bool:
        """Check if object exists by logical ID."""
        return self._namespace(logical_id) in self.objects
    
    def add_code(self, code: str, depends_on: Optional[List[str]] = None) -> None:
        """Add code snippet to the stack with dependency information."""
        self.code_stack.append(code)
    
    def get_available_objects(self) -> List[str]:
        """Get list of all created objects (returns logical IDs for templates)."""
        return [obj_id.replace(f"{self.scene_id}_", "") for obj_id in self.objects.keys()]
    
    def get_visible_objects(self) -> List[str]:
        """Get only visible objects (returns logical IDs)."""
        visible = [
            obj_id.replace(f"{self.scene_id}_", "") 
            for obj_id, obj in self.objects.items()
            if obj.state in [ObjectLifecycle.CREATED, ObjectLifecycle.VISIBLE]
        ]
        return visible
    
    def get_namespaced_id(self, logical_id: str) -> str:
        """Get the internal namespaced ID for a logical object ID."""
        return self._namespace(logical_id)
    
    def finalize(self) -> str:
        """Compile the full code from the composition context."""
        full_code = self.preamble
        
        # Add initialization section
        full_code += "        # --- Objects Initialization ---\n"
        for namespaced_id in self.object_order:
            obj = self.objects[namespaced_id]
            if obj.state != ObjectLifecycle.DESTROYED:
                logical_id = namespaced_id.replace(f"{self.scene_id}_", "")
                full_code += f"        # {logical_id}: {obj.object_type}\n"
                # Replace namespaced ID with logical ID in creation code
                creation_code = obj.creation_code.replace(namespaced_id, logical_id)
                full_code += creation_code
        
        full_code += "\n        # --- Animations ---\n"
        for code in self.code_stack:
            full_code += code
        
        full_code += self.postamble
        return full_code

class TemplateComposer:
    """Orchestrates composition of multiple templates with state management."""
    
    def __init__(self, scene_id: str, scene_description: str = ""):
        self.context = CompositionContext(scene_id=scene_id)
        self.scene_description = scene_description
        self.templates = []
    
    def add_template(self, template: "CompositionAwareTemplate") -> None:
        """Register a template to be composed."""
        self.templates.append(template)
    
    def compose(self) -> str:
        """Execute composition and return finalized code."""
        # Set up composition preamble
        self.context.preamble = "        # Scene initialization\n"
        
        # Execute each template in sequence
        for i, template in enumerate(self.templates):
            logger.debug(f"Composing template {i}: {template.__class__.__name__}")
            
            # Pass context to template
            template.set_composition_context(self.context)
            
            # Execute template
            template.compose()
        
        # Finalize and return code
        return self.context.finalize()

class CompositionAwareTemplate:
    """
    Base class for templates that support composition with state sharing.
    Uses logical object IDs (namespacing handled by context).
    """
    
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.context: Optional[CompositionContext] = None
        self.created_objects: List[str] = []  # Logical IDs
    
    def generate_construct_code(self) -> str:
        """
        Compatibility method to allow composition-aware templates 
        to be used in single-template mode.
        """
        composer = TemplateComposer("standalone")
        composer.add_template(self)
        # We need to strip the leading indentation from the finalized code
        # because the engine adds it back
        return composer.compose().replace("        ", "", 1)
    
    def set_composition_context(self, context: CompositionContext) -> None:
        """Provide the composition context to this template."""
        self.context = context
    
    def create_object(
        self,
        logical_id: str,
        obj_type: str,
        creation_code: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register an object in the composition.
        
        Args:
            logical_id: Logical name (e.g., "vector", "axes") - namespacing is automatic
            obj_type: 'axes', 'curve', 'point', 'vector', etc.
            creation_code: Manim code that creates the object
            data: Metadata about the object
        """
        if not self.context:
            raise RuntimeError("Composition context not set")
        
        self.context.add_object(logical_id, obj_type, creation_code, data)
        self.created_objects.append(logical_id)
    
    def add_animation_code(self, code: str) -> None:
        """Add animation code to the stack."""
        if not self.context:
            raise RuntimeError("Composition context not set")
        self.context.add_code(code)
    
    def object_exists(self, logical_id: str) -> bool:
        """Check if an object was created by previous templates."""
        if not self.context:
            return False
        return self.context.object_exists(logical_id)
    
    def get_available_objects(self) -> List[str]:
        """Query available objects from previous templates (logical IDs)."""
        if not self.context:
            return []
        return self.context.get_available_objects()
    
    def get_visible_objects(self) -> List[str]:
        """Get only visible objects from previous templates."""
        if not self.context:
            return []
        return self.context.get_visible_objects()
    
    def compose(self) -> None:
        """
        Execute the template composition logic.
        Override in subclasses to define the composition behavior.
        """
        raise NotImplementedError("Subclasses must implement compose()")
