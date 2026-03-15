from app.templates.engine import render_template, render_composed_scene
import json

print("--- UnitCircle ---")
try:
    print(render_template("unit_circle", {"color_cos": "ORANGE"}))
except Exception as e: print(e)

print("--- TrigWaves ---")
try:
    print(render_template("trig_waves", {"expression": "np.cos(x)"}))
except Exception as e: print(e)

print("--- Comparison ---")
try:
    print(render_composed_scene("comp", ["draw_curve", "draw_curve"], [
        {"expression": "np.sin(x)", "object_id": "c1"},
        {"expression": "np.cos(x)", "object_id": "c2"}
    ]))
except Exception as e: print(e)
