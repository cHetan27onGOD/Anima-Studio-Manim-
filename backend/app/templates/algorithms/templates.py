from typing import Any, Dict, List

from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, CompositionContext


class BFSTraversalTemplate(BaseTemplate):
    """Template for showing Breadth-First Search (BFS) on a graph."""

    def generate_construct_code(self) -> str:
        nodes = self.parameters.get("nodes", ["A", "B", "C", "D", "E", "F"])
        if not isinstance(nodes, list) or not nodes:
            nodes = ["A", "B", "C", "D", "E", "F"]
        nodes = [str(n) for n in nodes]

        traversal_order = self.parameters.get("traversal_order", nodes)
        if not isinstance(traversal_order, list) or not traversal_order:
            traversal_order = nodes
        traversal_order = [str(n) for n in traversal_order]

        code = f"        # BFS Traversal Pattern\n"
        code += f"        # Create graph structure\n"
        code += f"        nodes = {nodes}\n"
        code += "        dot_nodes = VGroup(*[Dot(radius=0.2, color=BLUE) for _ in range(len(nodes))])\n"
        code += "        dot_nodes.arrange_in_grid(rows=2, buff=1.5)\n"
        code += "        labels = VGroup(*[Text(str(n), font_size=20).next_to(d, UP, buff=0.1) for n, d in zip(nodes, dot_nodes)])\n"
        code += "\n"
        code += "        self.play(Create(dot_nodes), Write(labels))\n"
        code += "\n"
        code += "        # Animate traversal highlight\n"
        code += f"        traversal_order = {traversal_order}\n"
        code += "        for n_id in traversal_order:\n"
        code += "            idx = nodes.index(n_id) if n_id in nodes else 0\n"
        code += "            self.play(dot_nodes[idx].animate.set_color(YELLOW).scale(1.5), run_time=0.5)\n"
        code += "            self.wait(0.2)\n"
        code += "        self.wait(2)\n"
        return code


class BFSDFSComparisonTemplate(BaseTemplate):
    """Template for side-by-side BFS vs DFS traversal comparison."""

    def generate_construct_code(self) -> str:
        render_profile = self.parameters.get("render_profile", {})
        if not isinstance(render_profile, dict):
            render_profile = {}

        detail_level = str(
            self.parameters.get("detail_level", render_profile.get("detail_level", "standard"))
        ).lower()
        try:
            pace_scale = float(
                self.parameters.get("pace_scale", render_profile.get("pace_scale", 1.0))
            )
        except (TypeError, ValueError):
            pace_scale = 1.0
        pace_scale = max(0.6, min(2.0, pace_scale))

        nodes = self.parameters.get("nodes", ["A", "B", "C", "D", "E", "F"])
        if not isinstance(nodes, list) or not nodes:
            nodes = ["A", "B", "C", "D", "E", "F"]
        nodes = [str(n) for n in nodes]

        edges = self.parameters.get("edges", [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]])
        if not isinstance(edges, list) or not edges:
            edges = [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]]

        bfs_order = self.parameters.get("bfs_order", ["A", "B", "C", "D", "E", "F"])
        if not isinstance(bfs_order, list) or not bfs_order:
            bfs_order = ["A", "B", "C", "D", "E", "F"]
        bfs_order = [str(n) for n in bfs_order]

        dfs_order = self.parameters.get("dfs_order", ["A", "B", "D", "E", "C", "F"])
        if not isinstance(dfs_order, list) or not dfs_order:
            dfs_order = ["A", "B", "D", "E", "C", "F"]
        dfs_order = [str(n) for n in dfs_order]

        code = "        # BFS vs DFS Traversal Comparison\n"
        code += f"        detail_level = {repr(detail_level)}\n"
        code += f"        nodes = {nodes}\n"
        code += f"        edges = {edges}\n"
        code += f"        bfs_order = {bfs_order}\n"
        code += f"        dfs_order = {dfs_order}\n"
        code += "\n"
        code += (
            "        title = Text('BFS vs DFS Traversal', font_size=36, color=YELLOW).to_edge(UP)\n"
        )
        code += "        bfs_title = Text('BFS (level-order)', font_size=24, color=YELLOW).shift(LEFT*3.5 + UP*2.2)\n"
        code += "        dfs_title = Text('DFS (depth-first)', font_size=24, color=ORANGE).shift(RIGHT*3.5 + UP*2.2)\n"
        code += "\n"
        code += "        left_nodes = VGroup(*[Dot(radius=0.16, color=BLUE) for _ in range(len(nodes))])\n"
        code += "        right_nodes = VGroup(*[Dot(radius=0.16, color=BLUE) for _ in range(len(nodes))])\n"
        code += "        left_nodes.arrange_in_grid(rows=2, buff=1.0).shift(LEFT*3.5 + DOWN*0.1)\n"
        code += (
            "        right_nodes.arrange_in_grid(rows=2, buff=1.0).shift(RIGHT*3.5 + DOWN*0.1)\n"
        )
        code += "\n"
        code += "        left_labels = VGroup(*[Text(str(n), font_size=18).next_to(d, UP, buff=0.08) for n, d in zip(nodes, left_nodes)])\n"
        code += "        right_labels = VGroup(*[Text(str(n), font_size=18).next_to(d, UP, buff=0.08) for n, d in zip(nodes, right_nodes)])\n"
        code += "\n"
        code += "        left_edges = VGroup(*[Line(left_nodes[u].get_center(), left_nodes[v].get_center(), color=GRAY, stroke_opacity=0.5) for u, v in edges])\n"
        code += "        right_edges = VGroup(*[Line(right_nodes[u].get_center(), right_nodes[v].get_center(), color=GRAY, stroke_opacity=0.5) for u, v in edges])\n"
        code += "\n"
        code += f"        self.play(Write(title), run_time={1.0 * pace_scale:.2f})\n"
        code += f"        self.play(Write(bfs_title), Write(dfs_title), run_time={0.8 * pace_scale:.2f})\n"
        code += f"        self.play(Create(left_edges), Create(right_edges), Create(left_nodes), Create(right_nodes), Write(left_labels), Write(right_labels), run_time={1.2 * pace_scale:.2f})\n"
        code += "\n"
        code += "        bfs_markers = VGroup()\n"
        code += "        for step, n_id in enumerate(bfs_order, start=1):\n"
        code += "            idx = nodes.index(n_id) if n_id in nodes else 0\n"
        code += "            marker = Text(str(step), font_size=14, color=YELLOW).next_to(left_nodes[idx], DOWN, buff=0.05)\n"
        code += "            bfs_markers.add(marker)\n"
        code += f"            self.play(left_nodes[idx].animate.set_color(YELLOW).scale(1.15), FadeIn(marker), run_time={0.35 * pace_scale:.2f})\n"
        code += "\n"
        code += "        dfs_markers = VGroup()\n"
        code += "        for step, n_id in enumerate(dfs_order, start=1):\n"
        code += "            idx = nodes.index(n_id) if n_id in nodes else 0\n"
        code += "            marker = Text(str(step), font_size=14, color=ORANGE).next_to(right_nodes[idx], DOWN, buff=0.05)\n"
        code += "            dfs_markers.add(marker)\n"
        code += f"            self.play(right_nodes[idx].animate.set_color(ORANGE).scale(1.15), FadeIn(marker), run_time={0.35 * pace_scale:.2f})\n"
        code += "\n"

        code += "        if detail_level == 'advanced':\n"
        code += "            bfs_hint = Text('BFS: queue + level expansion', font_size=18, color=YELLOW).next_to(left_nodes, DOWN, buff=0.45)\n"
        code += "            dfs_hint = Text('DFS: stack/recursion + depth expansion', font_size=18, color=ORANGE).next_to(right_nodes, DOWN, buff=0.45)\n"
        code += f"            self.play(Write(bfs_hint), Write(dfs_hint), run_time={0.9 * pace_scale:.2f})\n"
        code += f"            self.play(Indicate(left_nodes[0]), Indicate(right_nodes[0]), run_time={0.7 * pace_scale:.2f})\n"
        code += "\n"

        code += "        takeaway = Text('BFS explores by level; DFS dives along a path first.', font_size=24).to_edge(DOWN)\n"
        code += f"        self.play(Write(takeaway), run_time={0.9 * pace_scale:.2f})\n"
        code += f"        self.wait({2.0 * pace_scale:.2f})\n"
        return code


# Phase 2: Advanced Algorithm Templates


class GraphVisualizationTemplate(CompositionAwareTemplate):
    """Base template for general graph visualization with nodes and edges."""

    def compose(self, context: "CompositionContext") -> None:
        nodes = self.parameters.get("nodes", ["A", "B", "C"])
        edges = self.parameters.get("edges", [[0, 1], [1, 2]])

        # Create node circles
        nodes_vgroup = (
            "        nodes = VGroup(*[Circle(0.2, color=BLUE) for _ in range(len(nodes))])\n"
        )
        context.add_obj("nodes", "group", nodes_vgroup)

        # Arrange nodes in a layout
        layout_code = "        nodes.arrange_in_grid(rows=2, buff=1.5)\n"
        context.add_anim(layout_code)

        # Create edges
        for edge in edges:
            edge_code = f"        edge_{edge[0]}_{edge[1]} = Line(nodes[{edge[0]}].get_center(), nodes[{edge[1]}].get_center())\n"
            context.add_obj(f"edge_{edge[0]}_{edge[1]}", "line", edge_code)


class DFSTraversalTemplate(CompositionAwareTemplate):
    """Template for Depth-First Search (DFS) visualization."""

    def compose(self, context: "CompositionContext") -> None:
        nodes = self.parameters.get("nodes", ["A", "B", "C", "D", "E"])

        # Graph structure
        graph_code = "        # Create graph with nodes\n"
        context.add_anim(graph_code)

        # DFS traversal order (root-first, depth-first)
        traversal = self.parameters.get("traversal_order", nodes)

        # Animate each node being visited
        for node in traversal:
            node_code = f"        # Visit {node}\n        self.wait(0.5)\n"
            context.add_anim(node_code)


class DijkstraTemplate(CompositionAwareTemplate):
    """Template for Dijkstra's shortest path algorithm visualization."""

    def compose(self, context: "CompositionContext") -> None:
        nodes = self.parameters.get("nodes", ["A", "B", "C", "D"])
        edges = self.parameters.get(
            "edges", [[0, 1, 4], [0, 2, 1], [2, 1, 2], [1, 3, 5]]
        )  # [u, v, weight]

        # Draw weighted graph
        code = f"        # Dijkstra Shortest Path Visualization\n"
        code += f"        nodes = VGroup(*[Circle(0.3, color=BLUE) for _ in {nodes}]).arrange_in_grid(rows=2, buff=2).center()\n"
        code += f"        labels = VGroup(*[Text(str(n), font_size=20).move_to(nodes[i]) for i, n in enumerate({nodes})])\n"
        code += f"        \n"

        # Edges with weights
        code += f"        edge_lines = VGroup()\n"
        code += f"        weight_labels = VGroup()\n"
        for u, v, w in edges:
            code += f"        e_{u}_{v} = Line(nodes[{u}].get_center(), nodes[{v}].get_center(), buff=0.3, color=GRAY)\n"
            code += (
                f"        w_{u}_{v} = Text('{w}', font_size=16).next_to(e_{u}_{v}, UP, buff=0.1)\n"
            )
            code += f"        edge_lines.add(e_{u}_{v})\n"
            code += f"        weight_labels.add(w_{u}_{v})\n"

        code += f"        self.play(Create(nodes), Write(labels), Create(edge_lines), Write(weight_labels))\n"
        code += f"        self.wait(1)\n"

        # Highlight path
        path = self.parameters.get("path", [0, 2, 1, 3])
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            code += f"        self.play(nodes[{u}].animate.set_color(YELLOW), nodes[{v}].animate.set_color(YELLOW))\n"
            code += f"        self.play(edge_lines[{i}].animate.set_color(YELLOW), run_time=0.5)\n"

        self.add_animation_code(code)


class TopologicalSortTemplate(CompositionAwareTemplate):
    """Template for topological sort visualization."""

    def compose(self, context: "CompositionContext") -> None:
        nodes = self.parameters.get("nodes", ["Task A", "Task B", "Task C"])

        # DAG (Directed Acyclic Graph)
        task_boxes = "        task_rects = VGroup(*[Rectangle(width=1, height=0.5, color=BLUE, fill_opacity=0.3) for _ in nodes])\n"
        context.add_obj("task_boxes", "group", task_boxes)

        # Arrange vertically for DAG
        arrange_code = "        task_rects.arrange(DOWN, buff=0.8)\n"
        context.add_anim(arrange_code)

        # Animate topological order
        for node in nodes:
            anim_code = f"        # Process {node} and its dependencies\n        self.wait(0.3)\n"
            context.add_anim(anim_code)


class SortingTemplate(BaseTemplate):
    """Template for showing sorting algorithms using bars."""

    def generate_construct_code(self) -> str:
        data = self.parameters.get("data", [4, 7, 2, 9, 1, 5])

        code = f"        # Sorting Algorithm Visualization\n"
        code += f"        bars = VGroup(*[Rectangle(width=0.8, height=val*0.5, color=BLUE, fill_opacity=0.7) for val in {data}])\n"
        code += f"        bars.arrange(RIGHT, buff=0.2, aligned_edge=DOWN).center()\n"
        code += f"        labels = VGroup(*[Text(str(val), font_size=24).next_to(bars[i], DOWN) for i, val in enumerate({data})])\n"
        code += f"        \n"
        code += f"        self.play(Create(bars), Write(labels))\n"
        code += f"        self.wait(1)\n"

        # Simple swap animation example (Bubble sort step)
        code += f"        # Example Swap\n"
        code += (
            f"        self.play(bars[0].animate.set_color(RED), bars[2].animate.set_color(RED))\n"
        )
        code += f"        self.play(\n"
        code += f"            bars[0].animate.move_to(bars[2].get_center()),\n"
        code += f"            bars[2].animate.move_to(bars[0].get_center()),\n"
        code += f"            run_time=1\n"
        code += f"        )\n"
        code += f"        self.wait(2)\n"
        return code
