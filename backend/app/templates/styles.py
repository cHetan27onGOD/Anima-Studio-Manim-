from typing import Any, Dict, Optional

STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "3b1b": {
        "background_color": "#0a0a0f",
        "primary_color": "BLUE",
        "secondary_color": "YELLOW",
        "accent_color": "GOLD",
        "text_color": "WHITE",
        "axis_color": "GREY",
        "font_size": 24,
    },
    "modern": {
        "background_color": "#000000",
        "primary_color": "#2563eb",  # Modern blue
        "secondary_color": "#db2777",  # Modern pink
        "accent_color": "#10b981",  # Modern green
        "text_color": "#f1f5f9",
        "axis_color": "#64748b",
        "font_size": 28,
    },
    "minimalist": {
        "background_color": "#18181b",
        "primary_color": "#fafafa",
        "secondary_color": "#71717a",
        "accent_color": "#3f3f46",
        "text_color": "#f4f4f5",
        "axis_color": "#27272a",
        "font_size": 20,
    },
    "dark": {
        "background_color": "#000000",
        "primary_color": "WHITE",
        "secondary_color": "GREY",
        "accent_color": "RED",
        "text_color": "WHITE",
        "axis_color": "GREY",
        "font_size": 24,
    },
}


def get_style(name: str) -> Dict[str, Any]:
    return STYLE_PRESETS.get(name.lower(), STYLE_PRESETS["3b1b"])
