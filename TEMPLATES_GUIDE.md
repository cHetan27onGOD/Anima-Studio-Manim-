# Beginner's Guide to AnimaStudio Templates 🎨

Welcome to AnimaStudio! This guide explains how our "AI-to-Animation" engine works and how you can use simple natural language to create beautiful math visualizations.

## How it Works: The 3-Step Flow

1.  **AI Planning**: When you enter a prompt (e.g., "Compare sine and cosine"), our AI analyzes it and creates a "Visual Plan".
2.  **The Template Library**: The plan uses our **Templates** (blueprints) to build your scene.
3.  **Manim Rendering**: Our system turns those templates into Python code and renders a video using **Manim** (the engine used by 3Blue1Brown).

---

## The Template Library 📚

Here are the blueprints available for your animations:

### 1. The Building Blocks (Primitives)
These are the small pieces you can mix and match.
*   **Draw Curve**: Draws any math function (e.g., `x**2`). Now supports comparisons!
*   **Place Point**: Highlights a specific spot on a graph.
*   **Draw Axis**: Sets up the grid and coordinate system.
*   **Write Text**: Adds labels or explanations.
*   **Draw Arrow**: Points to important things.

### 2. Specialized Math Templates
Ready-made patterns for specific topics:
*   **Unit Circle**: Shows how sine and cosine are related to a circle.
*   **Trig Waves**: Animates the generation of sine/cosine waves.
*   **Equation Solving**: Shows step-by-step algebraic solutions.
*   **Graph Visualization**: Draws connections between nodes (useful for networks).

---

## Pro-Tips for Your Prompts 💡

To get the best results, use these patterns in your natural language:

### For Comparisons (Multi-Graph)
> "Compare **cos(x)** and **cos(2x)**. Draw the first in **BLUE** and the second in **RED**. Label them both."
*   *What happens?*: The system uses two `Draw Curve` templates on the same set of axes.

### For Step-by-Step Transformations
> "Start with a **circle**, then **transform** it into a **square**, then highlight the corners."
*   *What happens?*: The system chains different templates and animations together.

### For Trigonometry
> "Show the **unit circle** with projections, then show the **sine wave** moving."
*   *What happens?*: The AI picks the `unit_circle` and `trig_waves` templates.

---

## Troubleshooting
*   **Labels look weird?**: I have fixed an issue where some characters (like 'theta') were cut off. They should now look perfect!
*   **Scaling is off?**: I have ensured that circles and graphs now fit perfectly on their axes.

Happy animating! 🚀
