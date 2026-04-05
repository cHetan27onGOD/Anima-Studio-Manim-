import ast
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Job, JobStatus
from app.schemas.animation import AnimationPlan
from app.services.llm import generate_manim_code, generate_plan
from app.templates.styles import get_style
from app.worker.celery_app import celery_app

# Create dedicated async engine for worker with NullPool
# NullPool ensures we don't share connections between event loops in Celery worker processes
worker_engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
WorkerAsyncSession = async_sessionmaker(worker_engine, class_=AsyncSession, expire_on_commit=False)

# Redis client for log streaming
redis_client = redis.Redis.from_url(settings.REDIS_URL)


def publish_log(job_id: str, message: str):
    try:
        redis_client.publish(f"logs:{job_id}", message)
    except Exception:
        pass


def parse_prompt(prompt: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Parse prompt to extract nodes and edges.

    Format: "A, B, C, A->B, B->C"
    Returns: (nodes, edges)
    """
    # Split by commas
    parts = [p.strip() for p in prompt.split(",")]

    nodes = []
    edges = []

    for part in parts:
        if "->" in part:
            # It's an edge
            source, target = part.split("->", 1)
            source = source.strip()
            target = target.strip()

            # Validate labels
            if not is_valid_label(source) or not is_valid_label(target):
                continue

            # Add nodes if not already present
            if source not in nodes:
                nodes.append(source)
            if target not in nodes:
                nodes.append(target)

            edges.append((source, target))
        else:
            # It's a node
            if is_valid_label(part) and part not in nodes:
                nodes.append(part)

    # Enforce limits
    nodes = nodes[: settings.MAX_NODES]
    edges = edges[: settings.MAX_EDGES]

    return nodes, edges


def is_valid_label(label: str) -> bool:
    """
    Validate node label.

    Only letters, numbers, spaces allowed. Max 20 chars.
    """
    if not label or len(label) > settings.MAX_LABEL_LENGTH:
        return False
    return bool(re.match(r"^[a-zA-Z0-9\s]+$", label))


def generate_manim_code_from_plan(plan: AnimationPlan, prompt: str) -> str:
    """
    Generate fresh Manim code directly via LLM, bypassing template routing.
    """
    return generate_manim_code(prompt, plan)


def validate_manim_code(code: str) -> List[str]:
    """Stage 6 — Code Validator.

    Runs ast.parse() on the generated Manim Python code before sending it
    to Docker. Catches syntax errors instantly (< 1 ms) vs. waiting 30-120s
    for Docker to fail.

    Returns:
        List of error strings (empty = valid syntax)
    """
    try:
        ast.parse(code)
        return []
    except SyntaxError as e:
        return [f"SyntaxError at line {e.lineno}: {e.msg} — {e.text!r}"]
    except Exception as e:
        return [f"Parse error: {e}"]


def _safe_identifier(name: str, fallback: str) -> str:
    ident = re.sub(r"[^0-9a-zA-Z_]", "_", str(name or "").strip())
    ident = re.sub(r"_+", "_", ident).strip("_")
    if not ident:
        ident = fallback
    if ident[0].isdigit():
        ident = f"{fallback}_{ident}"
    return ident


def _format_color(value: object) -> str:
    if isinstance(value, str) and re.fullmatch(r"[A-Z_]+", value):
        return value
    return repr(value)


def _render_plan_direct(plan: AnimationPlan) -> str:
    """Render a template-free plan into Manim code using primitives only."""
    style_name = plan.style or "3b1b"
    style = get_style(style_name)
    background_color = style.get("background_color", "#0d0f14")
    render_profile = plan.parameters.get("render_profile", {}) if isinstance(plan.parameters, dict) else {}
    frame_rate = render_profile.get("frame_rate", 30)

    code = (
        "from manim import *\n"
        "import numpy as np\n\n"
        f"config.background_color = '{background_color}'\n"
        f"config.frame_rate = {int(frame_rate)}\n\n"
        "class Scene1(Scene):\n"
        "    def construct(self):\n"
    )

    def _py(val: object) -> str:
        return repr(val)

    for scene in plan.scenes:
        objects = scene.objects or []
        animations = scene.animations or []
        id_map: dict[str, str] = {}

        for idx, obj in enumerate(objects, start=1):
            obj_id = _safe_identifier(obj.id, f"obj_{idx}")
            id_map[obj.id] = obj_id
            otype = (obj.type or "text").lower()
            params = obj.parameters or {}

            if otype == "text":
                text = _py(params.get("text", ""))
                font_size = params.get("font_size", 32)
                code += f"        {obj_id} = Text({text}, font_size={font_size})\n"
            elif otype in ("math_tex", "mathtex", "latex", "formula"):
                text = _py(params.get("text", "x"))
                code += f"        {obj_id} = MathTex({text})\n"
            elif otype == "line":
                start = params.get("start", [-1, 0, 0])
                end = params.get("end", [1, 0, 0])
                code += f"        {obj_id} = Line({_py(start)}, {_py(end)})\n"
            elif otype == "arrow":
                start = params.get("start", [-1, 0, 0])
                end = params.get("end", [1, 0, 0])
                code += f"        {obj_id} = Arrow({_py(start)}, {_py(end)})\n"
            elif otype == "dot":
                code += f"        {obj_id} = Dot(color=WHITE)\n"
            elif otype == "circle":
                radius = params.get("radius", 0.5)
                color = _format_color(params.get("color", "BLUE"))
                code += f"        {obj_id} = Circle(radius={radius}, color={color})\n"
            elif otype in ("node", "graph_node"):
                label = _py(params.get("label", obj_id))
                code += f"        {obj_id}_node = Circle(radius=0.45, color=BLUE)\n"
                code += f"        {obj_id}_label = Text({label}, font_size=20).move_to({obj_id}_node.get_center())\n"
                code += f"        {obj_id} = VGroup({obj_id}_node, {obj_id}_label)\n"
            else:
                # Fallback to text to avoid runtime errors
                text = _py(params.get("text", obj_id))
                code += f"        {obj_id} = Text({text}, font_size=24)\n"

            pos = params.get("position")
            if pos is not None:
                code += f"        {obj_id}.move_to({_py(pos)})\n"

        for step in animations:
            action = (step.action or "fade_in").lower()
            obj_id = id_map.get(step.object_id, _safe_identifier(step.object_id, "obj"))
            duration = float(step.duration or 1.0)
            params = step.parameters or {}

            if action == "write":
                code += f"        self.play(Write({obj_id}), run_time={duration:.2f})\n"
            elif action == "create":
                code += f"        self.play(Create({obj_id}), run_time={duration:.2f})\n"
            elif action == "fade_in":
                code += f"        self.play(FadeIn({obj_id}), run_time={duration:.2f})\n"
            elif action == "highlight":
                code += f"        self.play(Indicate({obj_id}), run_time={duration:.2f})\n"
            elif action == "color":
                color = _format_color(params.get("color", "YELLOW"))
                code += (
                    f"        self.play({obj_id}.animate.set_color({color}), run_time={duration:.2f})\n"
                )
            elif action == "move":
                to_pos = params.get("to", [0, 0, 0])
                code += (
                    f"        self.play({obj_id}.animate.move_to({_py(to_pos)}), run_time={duration:.2f})\n"
                )
            else:
                code += f"        self.play(FadeIn({obj_id}), run_time={duration:.2f})\n"

        code += "        self.wait(0.5)\n"

    return code


async def update_job_status(job_id: str, status: JobStatus, **kwargs):
    """Update job status in database."""
    async with WorkerAsyncSession() as session:
        async with session.begin():
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()

            if job:
                job.status = status
                for key, value in kwargs.items():
                    setattr(job, key, value)


@celery_app.task(
    name="app.worker.tasks.render_graph_task",
    bind=True,
    autoretry_for=(subprocess.TimeoutExpired,),
    retry_backoff=2,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def render_graph_task(self, job_id: str):
    """
    Celery task to render graph using Manim.
    """
    import asyncio

    # Ensure we have a fresh event loop for the worker thread
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(render_graph_async(job_id))
    except Exception as e:
        print(f"Task runner failed for job {job_id}: {str(e)}")
        # We don't have access to publish_log here without session,
        # but we can at least log to stdout for docker logs
        raise e
    finally:
        loop.close()


@celery_app.task(
    name="app.worker.tasks.render_custom_code_task",
    bind=True,
    autoretry_for=(subprocess.TimeoutExpired,),
    retry_backoff=2,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def render_custom_code_task(self, job_id: str):
    """
    Celery task to render custom Manim code.
    """
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(render_custom_code_async(job_id))
    except Exception as e:
        print(f"Custom task runner failed for job {job_id}: {str(e)}")
        raise e
    finally:
        loop.close()


async def render_custom_code_async(job_id: str):
    """
    Async function to handle custom code rendering.
    """
    logs = []
    try:
        # Check docker connectivity first
        try:
            subprocess.run(["docker", "ps"], capture_output=True, check=True, timeout=5)
        except Exception as e:
            raise Exception(
                f"Docker connection failed: {str(e)}. Ensure /var/run/docker.sock is mounted and permissions are correct."
            )

        await update_job_status(job_id, JobStatus.RUNNING)
        logs.append(f"Started custom code rendering for job {job_id}")
        publish_log(job_id, "Starting custom code render...")

        async with WorkerAsyncSession() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job or not job.code:
                raise Exception("Job or code not found")
            manim_code = job.code

        # Detect scene class name
        def _detect_scene_class(code: str) -> str:
            m = re.search(r"class\s+(\w+)\s*\((?:Scene|GraphScene|ThreeDScene)\)\s*:", code)
            return m.group(1) if m else "Scene1"

        scene_class = _detect_scene_class(manim_code)

        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(manim_code)
            scene_file = f.name

        output_filename = f"{job_id}.mp4"

        # Copy to renderer
        copy_cmd = [
            "docker",
            "exec",
            "-i",
            "anima_manim_renderer",
            "bash",
            "-c",
            "cat > /manim/scene.py",
        ]
        subprocess.run(copy_cmd, input=manim_code.encode(), capture_output=True, timeout=30)

        # Render
        docker_cmd = [
            "docker",
            "exec",
            "anima_manim_renderer",
            "manim",
            "-qh",
            "/manim/scene.py",
            scene_class,
            "-o",
            output_filename,
        ]
        render_process = subprocess.run(docker_cmd, capture_output=True, timeout=120, text=True)

        if render_process.returncode != 0:
            raise Exception(f"Manim render failed: {render_process.stderr}")

        # Copy output back using find to handle varying quality subdirectories
        copy_output_cmd = [
            "docker",
            "exec",
            "anima_manim_renderer",
            "bash",
            "-c",
            f"find /manim/media -name {output_filename} -exec cp {{}} /manim/outputs/ \\;",
        ]
        subprocess.run(copy_output_cmd, capture_output=True, timeout=30)

        logs.append(f"Custom render completed: {output_filename}")
        publish_log(job_id, "Custom render successful!")
        Path(scene_file).unlink(missing_ok=True)

        await update_job_status(
            job_id, JobStatus.SUCCEEDED, video_filename=output_filename, logs="\n".join(logs)
        )
        return {"status": "success", "video_filename": output_filename}

    except Exception as e:
        error_msg = str(e)
        logs.append(f"Error: {error_msg}")
        publish_log(job_id, f"Error: {error_msg}")
        await update_job_status(job_id, JobStatus.FAILED, error=error_msg, logs="\n".join(logs))
        return {"status": "failed", "error": error_msg}


async def render_graph_async(job_id: str):
    """
    Async function to handle graph rendering with LLM-generated plan (DSL).
    """
    logs = []

    try:
        # Check docker connectivity first
        try:
            subprocess.run(["docker", "ps"], capture_output=True, check=True, timeout=5)
        except Exception as e:
            raise Exception(
                f"Docker connection failed: {str(e)}. Ensure /var/run/docker.sock is mounted and permissions are correct."
            )

        # Update status to running
        await update_job_status(job_id, JobStatus.RUNNING)
        logs.append(f"Started rendering job {job_id}")
        publish_log(job_id, f"Started rendering job {job_id}")

        # Get job from database
        async with WorkerAsyncSession() as session:
            async with session.begin():
                result = await session.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()
                if not job:
                    raise Exception(f"Job {job_id} not found")
                prompt = job.prompt

        # Step 1: LLM Planner (DSL Generation)
        logs.append("Calling LLM Planner to generate DSL...")
        publish_log(job_id, "Planning animation scenes...")
        await update_job_status(job_id, JobStatus.RUNNING, progress=10)

        plan = generate_plan(prompt)
        logs.append(f"DSL Plan generated: {plan.title} ({len(plan.scenes)} scenes)")
        publish_log(job_id, f"Plan generated: {plan.title}")

        # If plan was rate-limited, record it so frontend can warn user
        if getattr(plan, "rate_limited", False):
            logs.append("Plan was rate-limited due to LLM quota")
            publish_log(job_id, "Plan hit LLM quota; using simplified fallback.")

        # Store plan in database
        plan_dict = plan.model_dump()
        await update_job_status(job_id, JobStatus.RUNNING, plan_json=plan_dict, progress=25)

        # Step 2: Prefer direct rendering for template-free BST plans.
        requirement_lock = (
            plan.parameters.get("input_understanding", {}).get("requirement_lock")
            if isinstance(plan.parameters, dict)
            else None
        )

        if requirement_lock == "bst_requirement_lock":
            logs.append("Rendering BST plan with direct renderer")
            publish_log(job_id, "Rendering BST plan directly (no templates)...")
            manim_code = _render_plan_direct(plan)
        else:
            use_direct_renderer = False
            if plan.scenes:
                use_direct_renderer = all(
                    (scene.template in {None, "generic"} and not (scene.templates or []))
                    for scene in plan.scenes
                )
                use_direct_renderer = use_direct_renderer and any(
                    (scene.objects or scene.animations) for scene in plan.scenes
                )

            if use_direct_renderer:
                logs.append("Rendering plan with direct renderer")
                publish_log(job_id, "Rendering plan directly (no templates)...")
                manim_code = _render_plan_direct(plan)
            else:
                logs.append("Rendering fresh scene-based Manim code")
                publish_log(job_id, "Generating fresh Manim code from current plan...")
                manim_code = generate_manim_code_from_plan(plan, prompt)

        await update_job_status(job_id, JobStatus.RUNNING, progress=50)

        def _detect_scene_class(code: str) -> str:
            # Fixed: was double-escaped so it never matched, always returning "Scene1"
            m = re.search(r"class\s+(\w+)\s*\((?:Scene|GraphScene|ThreeDScene)\)\s*:", code)
            return m.group(1) if m else "Scene1"

        scene_class = _detect_scene_class(manim_code)

        # ── Stage 6: Code Validator ────────────────────────────────────────
        syntax_errors = validate_manim_code(manim_code)
        if syntax_errors:
            error_detail = "; ".join(syntax_errors)
            logs.append(f"Stage 6 Code Validator: {error_detail}")
            publish_log(job_id, f"Syntax error in generated code: {error_detail}")
            raise Exception(f"Generated Manim code has syntax errors: {error_detail}")

        # Create temp file for scene
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(manim_code)
            scene_file = f.name

        # Generate unique output filename
        output_filename = f"{job_id}.mp4"
        # output path is container-managed; filename is used for DB record

        # Run Manim in Docker container
        logs.append("Starting Manim render in container")
        publish_log(job_id, "Starting Manim render in container")

        # Copy scene file to container and run manim
        docker_cmd = [
            "docker",
            "exec",
            "anima_manim_renderer",
            "manim",
            "-qh",
            "/manim/scene.py",
            scene_class,
            "-o",
            output_filename,
        ]

        # First copy the scene file into the container
        with open(scene_file, "r") as f:
            scene_content = f.read()

        copy_cmd = [
            "docker",
            "exec",
            "-i",
            "anima_manim_renderer",
            "bash",
            "-c",
            "cat > /manim/scene.py",
        ]

        copy_process = subprocess.run(
            copy_cmd, input=scene_content.encode(), capture_output=True, timeout=30
        )

        if copy_process.returncode != 0:
            raise Exception(f"Failed to copy scene file: {copy_process.stderr.decode()}")

        # Run manim render
        logs.append(f"Executing Manim render command: {' '.join(docker_cmd)}")
        publish_log(job_id, "Manim render starting (this may take a few minutes)...")

        # Update progress to 75%
        await update_job_status(job_id, JobStatus.RUNNING, progress=75)

        # Increased timeout to 300s for complex animations
        render_process = subprocess.run(docker_cmd, capture_output=True, timeout=300, text=True)

        if render_process.stdout:
            logs.append(f"Manim stdout:\n{render_process.stdout}")
        if render_process.stderr:
            logs.append(f"Manim stderr:\n{render_process.stderr}")

        publish_log(job_id, "Manim process finished, checking results...")

        if render_process.returncode != 0:
            error_msg = f"Manim render failed (code {render_process.returncode})"

            # Advanced Error Extraction Logic
            stderr_text = render_process.stderr or ""

            # Common Manim/Python Errors
            error_patterns = {
                r"NameError: name '(\w+)' is not defined": "Missing definition for: {0}",
                r"AttributeError: '(\w+)' object has no attribute '(\w+)'": "Object '{0}' has no property '{1}'",
                r"SyntaxError: (.*)": "Syntax Error: {0}",
                r"ModuleNotFoundError: No module named '(\w+)'": "Missing library: {0}",
                r"TypeError: (.*)": "Type Mismatch: {0}",
                r"ZeroDivisionError: (.*)": "Math Error: Division by zero",
            }

            for pattern, template in error_patterns.items():
                match = re.search(pattern, stderr_text)
                if match:
                    error_msg += f" - {template.format(*match.groups())}"
                    break
            else:
                # If no pattern matches, try to find the last line of the traceback
                lines = [line for line in stderr_text.strip().split("\n") if line.strip()]
                if lines:
                    error_msg += f" - {lines[-1]}"

            if "Scene1" not in manim_code and "scene_class" not in locals():
                error_msg += " (Note: No Scene class detected)"

            raise Exception(f"{error_msg}")

        # Update progress to 90%
        await update_job_status(job_id, JobStatus.RUNNING, progress=90)

        # Copy output from container to shared volume using find to handle varying quality subdirectories
        copy_output_cmd = [
            "docker",
            "exec",
            "anima_manim_renderer",
            "bash",
            "-c",
            f"find /manim/media -name {output_filename} -exec cp {{}} /manim/outputs/ \\;",
        ]

        copy_output_process = subprocess.run(copy_output_cmd, capture_output=True, timeout=30)

        if copy_output_process.returncode != 0:
            raise Exception(f"Failed to copy output: {copy_output_process.stderr.decode()}")

        # Cleanup: Remove scene file from container to keep it clean
        cleanup_cmd = ["docker", "exec", "anima_manim_renderer", "rm", "/manim/scene.py"]
        subprocess.run(cleanup_cmd, capture_output=True, timeout=10)

        logs.append(f"Render completed: {output_filename}")
        publish_log(job_id, f"Render completed: {output_filename}")

        # Clean up temp file
        Path(scene_file).unlink(missing_ok=True)

        # Update job with success
        await update_job_status(
            job_id,
            JobStatus.SUCCEEDED,
            video_filename=output_filename,
            code=manim_code,
            logs="\n".join(logs),
            progress=100,
        )

        return {"status": "success", "video_filename": output_filename}

    except Exception as e:
        error_msg = str(e)
        logs.append(f"Error: {error_msg}")
        publish_log(job_id, f"Error: {error_msg}")

        # Update job with failure
        await update_job_status(job_id, JobStatus.FAILED, error=error_msg, logs="\n".join(logs))

        return {"status": "failed", "error": error_msg}
