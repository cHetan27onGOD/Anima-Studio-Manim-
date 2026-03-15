from typing import Any, Dict, List
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate

class BFSTraversalTemplate(BaseTemplate):
    """Template for showing Breadth-First Search (BFS) on a graph."""
    
    def generate_construct_code(self) -> str:
        nodes = self.parameters.get("nodes", ["A", "B", "C", "D", "E"])
        
        code = f"        # BFS Traversal Pattern\n"
        code += f"        # Create graph structure\n"
        code += f"        dot_nodes = VGroup(*[Dot(radius=0.2, color=BLUE) for _ in '{nodes}'])\n"
        code += f"        dot_nodes.arrange_in_grid(rows=2, buff=1.5)\n"
        code += f"        labels = VGroup(*[Text(str(n), font_size=20).next_to(d, UP, buff=0.1) for n, d in zip({nodes}, dot_nodes)])\n"
        code += f"        \n"
        code += f"        self.play(Create(dot_nodes), Write(labels))\n"
        code += f"        \n"
        code += f"        # Animate traversal highlight\n"
        code += f"        traversal_order = {nodes}\n"
        code += f"        for n_id in traversal_order:\n"
        code += f"            idx = {nodes}.index(n_id)\n"
        code += f"            self.play(dot_nodes[idx].animate.set_color(YELLOW).scale(1.5), run_time=0.5)\n"
        code += f"            self.wait(0.2)\n"
        code += f"        self.wait(2)\n"
        return code

# Phase 2: Advanced Algorithm Templates

class GraphVisualizationTemplate(CompositionAwareTemplate):
    """Base template for general graph visualization with nodes and edges."""
    def compose(self) -> None:
        nodes = self.parameters.get("nodes", ["A", "B", "C"])
        edges = self.parameters.get("edges", [[0, 1], [1, 2]])
        
        # Create node circles
        nodes_vgroup = "        nodes = VGroup(*[Circle(0.2, color=BLUE) for _ in range(len(nodes))])\n"
        self.create_object("nodes", "group", nodes_vgroup)
        
        # Arrange nodes in a layout
        layout_code = "        nodes.arrange_in_grid(rows=2, buff=1.5)\n"
        self.add_animation_code(layout_code)
        
        # Create edges
        for edge in edges:
            edge_code = f"        edge_{edge} = Line(nodes[{edge[0]}].get_center(), nodes[{edge[1]}].get_center())\n"
            self.create_object(f"edge_{edge}", "line", edge_code)

class DFSTraversalTemplate(CompositionAwareTemplate):
    """Template for Depth-First Search (DFS) visualization."""
    def compose(self) -> None:
        nodes = self.parameters.get("nodes", ["A", "B", "C", "D", "E"])
        
        # Graph structure
        graph_code = "        # Create graph with nodes\n"
        self.add_animation_code(graph_code)
        
        # DFS traversal order (root-first, depth-first)
        traversal = self.parameters.get("traversal_order", nodes)
        
        # Animate each node being visited
        for node in traversal:
            node_code = f"        # Visit {node}\n        self.wait(0.5)\n"
            self.add_animation_code(node_code)

class DijkstraTemplate(CompositionAwareTemplate):
    """Template for Dijkstra's shortest path algorithm visualization."""
    def compose(self) -> None:
        nodes = self.parameters.get("nodes", ["A", "B", "C", "D"])
        edges = self.parameters.get("edges", [[0, 1, 4], [0, 2, 1], [2, 1, 2], [1, 3, 5]]) # [u, v, weight]
        
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
            code += f"        w_{u}_{v} = Text('{w}', font_size=16).next_to(e_{u}_{v}, UP, buff=0.1)\n"
            code += f"        edge_lines.add(e_{u}_{v})\n"
            code += f"        weight_labels.add(w_{u}_{v})\n"
        
        code += f"        self.play(Create(nodes), Write(labels), Create(edge_lines), Write(weight_labels))\n"
        code += f"        self.wait(1)\n"
        
        # Highlight path
        path = self.parameters.get("path", [0, 2, 1, 3])
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            code += f"        self.play(nodes[{u}].animate.set_color(YELLOW), nodes[{v}].animate.set_color(YELLOW))\n"
            code += f"        self.play(edge_lines[{i}].animate.set_color(YELLOW), run_time=0.5)\n"
        
        self.add_animation_code(code)

class TopologicalSortTemplate(CompositionAwareTemplate):
    """Template for topological sort visualization."""
    def compose(self) -> None:
        nodes = self.parameters.get("nodes", ["Task A", "Task B", "Task C"])
        
        # DAG (Directed Acyclic Graph)
        task_boxes = "        task_rects = VGroup(*[Rectangle(width=1, height=0.5, color=BLUE, fill_opacity=0.3) for _ in nodes])\n"
        self.create_object("task_boxes", "group", task_boxes)
        
        # Arrange vertically for DAG
        arrange_code = "        task_rects.arrange(DOWN, buff=0.8)\n"
        self.add_animation_code(arrange_code)
        
        # Animate topological order
        for node in nodes:
            anim_code = f"        # Process {node} and its dependencies\n        self.wait(0.3)\n"
            self.add_animation_code(anim_code)

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
        code += f"        self.play(bars[0].animate.set_color(RED), bars[2].animate.set_color(RED))\n"
        code += f"        self.play(\n"
        code += f"            bars[0].animate.move_to(bars[2].get_center()),\n"
        code += f"            bars[2].animate.move_to(bars[0].get_center()),\n"
        code += f"            run_time=1\n"
        code += f"        )\n"
        code += f"        self.wait(2)\n"
        return code
    """Template for topological sort visualization."""
    def compose(self) -> None:
        nodes = self.parameters.get("nodes", ["Task A", "Task B", "Task C"])
        
        # DAG (Directed Acyclic Graph)
        task_boxes = "        task_rects = VGroup(*[Rectangle(width=1, height=0.5, color=BLUE, fill_opacity=0.3) for _ in nodes])\n"
        self.create_object("task_boxes", "group", task_boxes)
        
        # Arrange vertically for DAG
        arrange_code = "        task_rects.arrange(DOWN, buff=0.8)\n"
        self.add_animation_code(arrange_code)
        
        # Animate topological order
        for node in nodes:
            anim_code = f"        # Process {node} and its dependencies\n        self.wait(0.3)\n"
            self.add_animation_code(anim_code)
