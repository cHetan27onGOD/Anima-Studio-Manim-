# Physics & Chemistry Formula Display Guide

## Goal
Enable Anima Studio to recognize physics and chemistry concepts in user prompts and automatically display their formulas alongside animations.

**Example prompts:**
- "Explain Newton's Second Law" → displays `F = ma`
- "Show kinetic energy formula" → displays `KE = ½mv²`
- "Visualize water molecule" → displays `H₂O` formula
- "Explain molar mass calculation" → displays formula + calculation

---

## Architecture Overview

```
User Prompt: "Explain Newton's Second Law"
    ↓
LLM Planner (llm.py)
├─ rule_based_concept_router()
├─ Detect: "newton" + "force" → category="physics"
└─ Extract: "Newton's Second Law"
    ↓
New: Physics/Chemistry Formula Router
├─ physics_formula_map.get("Newton's Second Law")
└─ Return: formula_string = "F = ma"
    ↓
Template Engine (engine.py)
├─ Render animation template
├─ NEW: Inject formula display layer
└─ Add formula as text object in scene
    ↓
Manim Code Generation
└─ Scene now includes formula visualization
    ↓
Final Video
└─ Animation + Formula displayed together
```

---

## Implementation Steps

### **STEP 1: Create Physics Formulas Module**

**File:** `backend/app/templates/physics.py`

```python
"""Physics formula templates and mappings."""

from typing import Dict, Tuple
from app.templates.composition import CompositionAwareTemplate

# Physics Concepts → (Formula, LaTeX, Description)
PHYSICS_FORMULAS: Dict[str, Tuple[str, str, str]] = {
    # Mechanics
    "Newton's Second Law": ("F = ma", "F = ma", "Force equals mass times acceleration"),
    "kinetic energy": ("KE = ½mv²", "KE = \\frac{1}{2}mv^2", "Kinetic energy of moving object"),
    "potential energy": ("PE = mgh", "PE = mgh", "Gravitational potential energy"),
    "momentum": ("p = mv", "p = mv", "Linear momentum"),
    "work": ("W = Fd", "W = Fd", "Work done by force"),
    "power": ("P = W/t", "P = \\frac{W}{t}", "Power is work over time"),
    "impulse": ("J = FΔt", "J = F\\Delta t", "Impulse equals force times time"),
    
    # Waves & Vibrations
    "frequency": ("f = 1/T", "f = \\frac{1}{T}", "Frequency is reciprocal of period"),
    "wave speed": ("v = fλ", "v = f\\lambda", "Wave speed equals frequency times wavelength"),
    "Doppler effect": ("f' = f(v ± vo)/(v ∓ vs)", "f' = f\\frac{v \\pm v_o}{v \\mp v_s}", "Observed frequency with motion"),
    
    # Thermodynamics
    "ideal gas law": ("PV = nRT", "PV = nRT", "Ideal gas equation of state"),
    "heat capacity": ("Q = mcΔT", "Q = mc\\Delta T", "Heat absorbed by substance"),
    "entropy change": ("ΔS = Q/T", "\\Delta S = \\frac{Q}{T}", "Change in entropy"),
    
    # Electromagnetism
    "Coulomb's law": ("F = k(q₁q₂/r²)", "F = k\\frac{q_1 q_2}{r^2}", "Electric force between charges"),
    "Ohm's law": ("V = IR", "V = IR", "Voltage equals current times resistance"),
    "power dissipation": ("P = I²R = V²/R", "P = I^2R = \\frac{V^2}{R}", "Electrical power"),
    "electromagnetic induction": ("ε = -dΦ/dt", "\\varepsilon = -\\frac{d\\Phi}{dt}", "Faraday's law"),
    
    # Optics
    "lens formula": ("1/f = 1/o + 1/i", "\\frac{1}{f} = \\frac{1}{o} + \\frac{1}{i}", "Thin lens equation"),
    "magnification": ("m = -i/o", "m = -\\frac{i}{o}", "Lens magnification"),
    "Snell's law": ("n₁sin(θ₁) = n₂sin(θ₂)", "n_1\\sin(\\theta_1) = n_2\\sin(\\theta_2)", "Refraction law"),
    
    # Modern Physics
    "mass energy equivalence": ("E = mc²", "E = mc^2", "Energy-mass equivalence"),
    "photon energy": ("E = hf = hc/λ", "E = hf = \\frac{hc}{\\lambda}", "Photon energy"),
}

def get_physics_formula(concept: str) -> Dict[str, str]:
    """
    Get physics formula for a concept.
    
    Args:
        concept: Physics concept name (e.g., "kinetic energy")
    
    Returns:
        {
            "name": "Kinetic Energy",
            "formula": "KE = ½mv²",
            "latex": "KE = \\frac{1}{2}mv^2",
            "description": "..."
        }
    """
    concept_lower = concept.lower()
    
    for key, (formula, latex, desc) in PHYSICS_FORMULAS.items():
        if concept_lower in key.lower() or key.lower() in concept_lower:
            return {
                "name": key.title(),
                "formula": formula,
                "latex": latex,
                "description": desc
            }
    
    return None


class PhysicsFormulaTemplate(CompositionAwareTemplate):
    """Display physics formula in a scene."""
    
    def compose(self) -> None:
        concept = self.parameters.get("concept", "")
        
        formula_data = get_physics_formula(concept)
        if not formula_data:
            return
        
        # Create formula display code
        latex_str = formula_data["latex"]
        formula_code = f"""
        formula = MathTex("{latex_str}", font_size=48, color=YELLOW)
        formula.to_corner(UP)
        label = Text("{formula_data['name']}", font_size=24, color=WHITE)
        label.next_to(formula, DOWN, buff=0.5)
        
        self.play(Write(formula), Write(label))
        self.wait(2)
"""
        self.create_object("formula", "text", formula_code, {
            "latex": latex_str,
            "name": formula_data["name"]
        })
        self.add_animation_code(formula_code)
```

---

### **STEP 2: Create Chemistry Formulas Module**

**File:** `backend/app/templates/chemistry.py`

```python
"""Chemistry formula templates and molecular structures."""

from typing import Dict, Tuple
from app.templates.composition import CompositionAwareTemplate

# Chemistry Concepts → (Molecular Formula, IUPAC Name, Description)
CHEMISTRY_FORMULAS: Dict[str, Tuple[str, str, str]] = {
    # Basic Molecules
    "water": ("H₂O", "Dihydrogen Monoxide", "Universal solvent, essential for life"),
    "carbon dioxide": ("CO₂", "Carbon Dioxide", "Greenhouse gas, used in photosynthesis"),
    "oxygen": ("O₂", "Oxygen Gas", "Diatomic oxygen, required for respiration"),
    "nitrogen": ("N₂", "Nitrogen Gas", "Diatomic nitrogen, major atmospheric component"),
    "glucose": ("C₆H₁₂O₆", "Hexose", "Simple sugar, primary energy source"),
    "ethanol": ("C₂H₅OH", "Ethanol", "Alcohol, used in beverages and fuel"),
    "methane": ("CH₄", "Methane", "Natural gas, major greenhouse gas"),
    "ammonia": ("NH₃", "Ammonia", "Nitrogen compound, industrial importance"),
    
    # Acids & Bases
    "hydrochloric acid": ("HCl", "Hydrogen Chloride", "Strong acid, stomach acid"),
    "sulfuric acid": ("H₂SO₄", "Sulfuric Acid", "Diprotic strong acid"),
    "acetic acid": ("CH₃COOH", "Acetic Acid", "Weak acid, found in vinegar"),
    "sodium hydroxide": ("NaOH", "Sodium Hydroxide", "Strong base, caustic soda"),
    "ammonia solution": ("NH₃ + H₂O", "Aqueous Ammonia", "Weak base"),
    
    # Salts
    "sodium chloride": ("NaCl", "Sodium Chloride", "Table salt, ionic compound"),
    "calcium carbonate": ("CaCO₃", "Calcium Carbonate", "Limestone, chalk"),
    "magnesium oxide": ("MgO", "Magnesium Oxide", "Ionic compound, ionic bonding example"),
    
    # Organic Molecules
    "benzene": ("C₆H₆", "Benzene", "Aromatic hydrocarbon, resonance structure"),
    "toluene": ("C₇H₈", "Toluene", "Methylbenzene, organic solvent"),
    "aspirin": ("C₉H₈O₄", "Acetylsalicylic Acid", "Pain reliever drug"),
    
    # Common Reactions
    "combustion": ("CₓHₓ + O₂ → CO₂ + H₂O", "Combustion Reaction", "Exothermic oxidation"),
    "photosynthesis": ("CO₂ + H₂O → C₆H₁₂O₆ + O₂", "Photosynthesis", "Light-driven reaction"),
    "neutralization": ("HCl + NaOH → NaCl + H₂O", "Acid-Base Neutralization", "Produces salt and water"),
}

def get_chemistry_formula(concept: str) -> Dict[str, str]:
    """
    Get chemistry formula for a concept.
    
    Args:
        concept: Chemistry concept name
    
    Returns:
        {
            "name": "Water",
            "formula": "H₂O",
            "iupac": "Dihydrogen Monoxide",
            "description": "..."
        }
    """
    concept_lower = concept.lower()
    
    for key, (formula, iupac, desc) in CHEMISTRY_FORMULAS.items():
        if concept_lower in key.lower() or key.lower() in concept_lower:
            return {
                "name": key.title(),
                "formula": formula,
                "iupac": iupac,
                "description": desc
            }
    
    return None


class ChemistryFormulaTemplate(CompositionAwareTemplate):
    """Display chemistry formula and molecular structure."""
    
    def compose(self) -> None:
        concept = self.parameters.get("concept", "")
        
        formula_data = get_chemistry_formula(concept)
        if not formula_data:
            return
        
        # Create molecular formula display
        formula_code = f"""
        # Chemistry Formula Display
        formula = Text("{formula_data['formula']}", font_size=40, color=BLUE_C)
        name = Text("{formula_data['name']}", font_size=20, color=WHITE)
        iupac = Text("IUPAC: {formula_data['iupac']}", font_size=16, color=GRAY_C)
        
        group = VGroup(formula, name, iupac).arrange(DOWN, buff=0.3)
        group.to_corner(UP)
        
        self.play(FadeIn(group))
        self.wait(3)
"""
        self.create_object("chem_formula", "text", formula_code, {
            "formula": formula_data["formula"],
            "name": formula_data["name"]
        })
        self.add_animation_code(formula_code)
```

---

### **STEP 3: Register Templates in Engine**

**File:** `backend/app/templates/engine.py` (Add to TEMPLATES dict)

```python
from app.templates.physics import PhysicsFormulaTemplate
from app.templates.chemistry import ChemistryFormulaTemplate

TEMPLATES: Dict[str, Type[BaseTemplate]] = {
    # ... existing templates ...
    
    # NEW: Physics & Chemistry
    "physics_formula": PhysicsFormulaTemplate,
    "chemistry_formula": ChemistryFormulaTemplate,
}
```

---

### **STEP 4: Update LLM Router**

**File:** `backend/app/services/llm.py`

Add this to `rule_based_concept_router()`:

```python
def rule_based_concept_router(prompt: str) -> Optional[UserIntent]:
    """Lightweight concept detection for routing."""
    p = prompt.lower()
    
    # ... existing code ...
    
    # NEW: Physics Concepts
    physics_keywords = {
        "newton": "physics_formula", "force": "physics_formula",
        "kinetic energy": "physics_formula", "potential energy": "physics_formula",
        "momentum": "physics_formula", "wave": "physics_formula",
        "frequency": "physics_formula", "thermodynamics": "physics_formula",
        "coulomb": "physics_formula", "ohm's law": "physics_formula",
        "lens": "physics_formula", "refraction": "physics_formula",
        "E=mc²": "physics_formula", "photon": "physics_formula",
    }
    
    for keyword, template in physics_keywords.items():
        if keyword in p:
            return UserIntent(concept=keyword, template=template)
    
    # NEW: Chemistry Concepts
    chemistry_keywords = {
        "water": "chemistry_formula", "H₂O": "chemistry_formula",
        "carbon dioxide": "chemistry_formula", "CO₂": "chemistry_formula",
        "glucose": "chemistry_formula", "ethanol": "chemistry_formula",
        "acid": "chemistry_formula", "base": "chemistry_formula",
        "salt": "chemistry_formula", "molecule": "chemistry_formula",
        "benzene": "chemistry_formula", "combustion": "chemistry_formula",
        "photosynthesis": "chemistry_formula", "neutralization": "chemistry_formula",
    }
    
    for keyword, template in chemistry_keywords.items():
        if keyword in p:
            return UserIntent(concept=keyword, template=template)
    
    # ... rest of existing code ...
```

---

### **STEP 5: Update LLM Planner Prompt**

**File:** `backend/app/services/llm.py`

Add to `COMBINED_PLANNER_PROMPT`:

```
**Physics Formulas (NEW):**
- physics_formula: Display physics equation (F=ma, E=mc², etc.)

**Chemistry Formulas (NEW):**
- chemistry_formula: Display molecular formula (H₂O, CO₂, etc.)

COMPOSITION TEMPLATES:
- [existing templates...]
- physics_formula: Show physics equation with description
- chemistry_formula: Show chemical structure with IUPAC name
```

---

### **STEP 6: Create Capability Registry Entries**

**File:** `backend/app/templates/capabilities.py`

Add to `initialize_all_capabilities()`:

```python
from app.templates.physics import get_physics_formula
from app.templates.chemistry import get_chemistry_formula

# Physics Templates
register_template_capabilities(
    "physics_formula",
    concepts={
        "newton", "force", "kinetic energy", "potential energy",
        "momentum", "wave", "frequency", "thermodynamics",
        "coulomb", "ohm", "lens", "refraction", "photon", "E=mc²"
    },
    composition_ready=True,
    duration=6.0,
    name="Physics Formula Display"
)

# Chemistry Templates
register_template_capabilities(
    "chemistry_formula",
    concepts={
        "water", "H₂O", "carbon dioxide", "CO₂", "glucose",
        "ethanol", "acid", "base", "salt", "molecule",
        "benzene", "combustion", "photosynthesis", "neutralization"
    },
    composition_ready=True,
    duration=5.0,
    name="Chemistry Formula Display"
)
```

---

## Testing & Validation

### **Test Case 1: Physics Formula Display**

```bash
# Terminal
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain Newton Second Law with F equals ma formula"}'
```

**Expected output:**
- ✅ Scene displays formula: F = ma
- ✅ Description: "Force equals mass times acceleration"
- ✅ Duration: ~6 seconds

---

### **Test Case 2: Chemistry Formula Display**

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show water molecule formula H2O"}'
```

**Expected output:**
- ✅ Scene displays: H₂O
- ✅ IUPAC name displayed
- ✅ Duration: ~5 seconds

---

### **Test Case 3: Combined Animation**

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain kinetic energy formula with example of moving ball"}'
```

**Expected flow:**
1. Scene 1: Animation of moving ball
2. Scene 2: Display KE = ½mv² formula
3. Scene 3: Calculation example

---

## Validation Checklist

- [ ] Files created: `physics.py`, `chemistry.py`
- [ ] Templates registered in `engine.py` TEMPLATES dict
- [ ] Capabilities registered in `capabilities.py`
- [ ] LLM router updated with physics/chemistry keywords
- [ ] COMBINED_PLANNER_PROMPT updated with formula templates
- [ ] Test Case 1 passes (Newton's Law)
- [ ] Test Case 2 passes (Water molecule)
- [ ] Test Case 3 passes (Combined animation)
- [ ] No errors in logs: `docker-compose logs -f backend`
- [ ] Videos render without syntax errors

---

## Troubleshooting

### **Problem: Formula not displaying**

**Solutions:**
1. Check concept name matches exactly in `PHYSICS_FORMULAS` or `CHEMISTRY_FORMULAS` dict
2. Verify LLM prompt includes formula template concept
3. Check logs: `docker-compose logs backend | grep formula`

### **Problem: LaTeX rendering fails in Manim**

**Solutions:**
1. Ensure LaTeX special characters are properly escaped
2. Use `r""` raw strings for LaTeX: `r"E=mc^2"`
3. Test LaTeX syntax: `python -c "from manim import *; print(MathTex(r'E=mc^2'))"`

### **Problem: Router not detecting formula concept**

**Solutions:**
1. Add more keyword aliases in router
2. Use capability fallback (already implemented)
3. Check `rule_based_concept_router()` detects keyword in lowercase

---

## Extension Ideas

### Add More Physics Formulas
```python
# Add to PHYSICS_FORMULAS dict:
"relativity": ("γ = 1/√(1-v²/c²)", "\\gamma = \\frac{1}{\\sqrt{1-v^2/c^2}}", "Lorentz factor"),
"quantum": ("E = hf", "E = hf", "Photon energy"),
```

### Add More Chemistry Formulas
```python
# Add to CHEMISTRY_FORMULAS dict:
"DNA": ("C₁₀H₁₃N₄O₂", "Deoxyadenosine", "DNA building block"),
"ATP": ("C₁₀H₁₆N₅O₁₃P₃", "Adenosine Triphosphate", "Energy molecule"),
```

### Interactive Formula Exploration
```python
# Future: Add animation showing formula derivation
class PhysicsDerivationTemplate(CompositionAwareTemplate):
    """Animate formula derivation step-by-step."""
    def compose(self):
        # Show: F = ma ← derived from assumptions
        # Show: a = Δv/Δt
        # Combine: F = m(Δv/Δt)
```

---

## Summary

You now have a complete system to:
1. ✅ Recognize physics/chemistry concepts in prompts
2. ✅ Automatically display relevant formulas
3. ✅ Integrate formulas into animations
4. ✅ Render beautiful LaTeX equations
5. ✅ Extend with new formulas easily

**Next: Run test cases and iterate!**
