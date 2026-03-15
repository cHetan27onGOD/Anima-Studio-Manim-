# Adding Physics / Chemistry Formula Templates (Manim + LLM)

This guide shows how to add an educational formula animation template to Anima Studio using **Manim** (MathTex) and the existing LLM planning pipeline.

---

## 1) Why this works

- The rendering backend is **Manim**, which supports LaTeX formulas via `MathTex(...)`.  
- The LLM planner creates a structured `AnimationPlan` that maps to a **template**.
- You can add a new template that renders a formula and then teach the planner to pick that template.

---

## 2) Create a new template (formula display)

Create a new file under `backend/app/templates/` (example: `formula.py`).

```python
from app.templates.base import BaseTemplate

class FormulaTemplate(BaseTemplate):
    """Displays a formula using Manim MathTex."""

    def generate_construct_code(self) -> str:
        formula = self.parameters.get("formula", r"E=mc^2")
        code  = "        # Physics/Chemistry formula display\n"
        code += f"        formula = MathTex(r'{{formula}}').scale(1.8)\n"
        code += "        formula.to_edge(UP)\n"
        code += "        self.play(Write(formula))\n"
        code += "        self.wait(2)\n"
        return code
```

Then register it in the template registry (location depends on your system; likely in `backend/app/templates/__init__.py` or similar).

---

## 3) Route prompts to the formula template

Update the concept router in `backend/app/services/llm.py`:

```python
if "E=mc^2" in p or "kinetic energy" in p:
    return UserIntent(concept="energy_formula", template="formula")

if "H2O" in p or "chemical formula" in p:
    return UserIntent(concept="chemical_formula", template="formula")
```

This makes prompts like _“Explain E=mc^2”_ use the new template.

---

## 4) Example prompt (for testing)

Use the frontend or API to send a prompt such as:

- **“Show the formula for kinetic energy and explain each term.”**
- **“Display the chemical formula for water (H2O) with an explanation.”**


---

## 5) Validating in code

Run the unit tests to ensure the new template is discoverable and the planner works:

```bash
docker exec anima_api python -m pytest backend/test_llm.py -v
```

---

## 6) Notes for Claude-based editing

If you’re using Claude to edit this file, you can:
1. Add more template examples (e.g., physics, chemistry, math symbols).  
2. Expand the router rules to detect more formula-related keywords.  
3. Add a small “demo prompt → expected plan” section for documentation.

---

## 7) Optional: Render a multi-step explanation

If you want step-by-step animations (like building a formula piece-by-piece), you can write a template that uses multiple `MathTex` objects and animates them sequentially.

Example:

```python
code += "        eq1 = MathTex(r'E=mc^2').to_edge(UP)\n"
code += "        eq2 = MathTex(r'K=1/2 mv^2').next_to(eq1, DOWN)\n"
code += "        self.play(Write(eq1))\n"
code += "        self.wait(1)\n"
code += "        self.play(Transform(eq1, eq2))\n"
```

---

That’s it — with this template in place, Anima Studio can generate formula animations on demand.
