from typing import Any, Dict, List
from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate

class NeuralNetworkTemplate(BaseTemplate):
    """Template for 3Blue1Brown style Neural Network architectures."""
    
    def generate_construct_code(self) -> str:
        layers = self.parameters.get("layers", [3, 4, 2])
        code = f"        # Neural Network Pattern\n"
        code += f"        layers = {layers}\n"
        code += f"        v_spacing = 1.0\n"
        code += f"        h_spacing = 2.5\n"
        code += f"        \n"
        code += f"        all_layers = []\n"
        code += f"        for l_idx, size in enumerate(layers):\n"
        code += f"            layer_nodes = VGroup(*[Circle(radius=0.3, color=BLUE_C, stroke_width=2) for _ in range(size)])\n"
        code += f"            layer_nodes.arrange(DOWN, buff=v_spacing)\n"
        code += f"            layer_nodes.move_to([l_idx * h_spacing - (len(layers)-1)*h_spacing/2, 0, 0])\n"
        code += f"            all_layers.append(layer_nodes)\n"
        code += f"            self.play(Create(layer_nodes))\n"
        code += f"            self.wait(0.5)\n"
        code += f"        \n"
        code += f"        # Connect layers\n"
        code += f"        for i in range(len(all_layers)-1):\n"
        code += f"            for start in all_layers[i]:\n"
        code += f"                for end in all_layers[i+1]:\n"
        code += f"                    line = Line(start.get_right(), end.get_left(), stroke_width=1, stroke_opacity=0.3, color=WHITE)\n"
        code += f"                    self.add(line)\n"
        code += f"        self.wait(2)\n"
        return code

class TransformerAttentionTemplate(BaseTemplate):
    """Template for 3Blue1Brown style Transformer Attention mechanisms."""
    
    def generate_construct_code(self) -> str:
        tokens = self.parameters.get("tokens", ["Token 1", "Token 2", "Token 3"])
        code = f"        # Transformer Attention Pattern\n"
        code += f"        tokens = {tokens}\n"
        code += f"        token_boxes = VGroup(*[Rectangle(width=1.5, height=0.8, color=TEAL, fill_opacity=0.2) for _ in tokens])\n"
        code += f"        token_boxes.arrange(DOWN, buff=0.5).to_edge(LEFT, buff=1)\n"
        code += f"        \n"
        code += f"        labels = VGroup(*[Text(t, font_size=24) for t in tokens])\n"
        code += f"        for box, label in zip(token_boxes, labels):\n"
        code += f"            label.move_to(box.get_center())\n"
        code += f"        \n"
        code += f"        attention_block = Rectangle(width=3, height=5, color=GOLD, fill_opacity=0.1).center()\n"
        code += f"        attn_text = Text('Attention Mechanism', font_size=32, color=GOLD).next_to(attention_block, UP)\n"
        code += f"        \n"
        code += f"        self.play(Create(token_boxes), Write(labels))\n"
        code += f"        self.play(Create(attention_block), Write(attn_text))\n"
        code += f"        \n"
        code += f"        # Animate attention flow\n"
        code += f"        for box in token_boxes:\n"
        code += f"            line = Line(box.get_right(), attention_block.get_left(), color=GOLD_A, stroke_width=2)\n"
        code += f"            self.play(ShowPassingFlash(line), run_time=1)\n"
        code += f"        \n"
        code += f"        self.wait(2)\n"
        return code

# Phase 2: Advanced Machine Learning Templates

class BackpropagationTemplate(CompositionAwareTemplate):
    """Template for visualizing backpropagation through a network."""
    def compose(self) -> None:
        # Simple network: input -> hidden -> output
        input_code = "        input_layer = VGroup(*[Circle(0.2, color=BLUE) for _ in range(3)])\n"
        self.create_object("input_layer", "layer", input_code)
        
        hidden_code = "        hidden_layer = VGroup(*[Circle(0.2, color=GREEN) for _ in range(4)])\n"
        self.create_object("hidden_layer", "layer", hidden_code)
        
        output_code = "        output_layer = VGroup(*[Circle(0.2, color=RED) for _ in range(2)])\n"
        self.create_object("output_layer", "layer", output_code)
        
        # Forward pass
        forward_code = "        # Forward Pass: Input -> Hidden -> Output\n        self.play(Create(input_layer), Create(hidden_layer), Create(output_layer))\n"
        self.add_animation_code(forward_code)
        
        # Backward pass
        backward_code = "        # Backward Pass: Gradient flow\n        self.wait(1)\n"
        self.add_animation_code(backward_code)

class EmbeddingSpaceTemplate(CompositionAwareTemplate):
    """Template for visualizing word/token embeddings in vector space."""
    def compose(self) -> None:
        # 2D or 3D embedding space
        axes_code = "        ax = Axes(x_range=[-2, 2], y_range=[-2, 2])\n"
        self.create_object("axes", "axes", axes_code)
        
        # Words as points
        words = self.parameters.get("words", ["king", "queen", "man", "woman"])
        
        # Create word points
        for i, word in enumerate(words):
            point_code = f"        {word}_point = Dot(ax.c2p({i % 2}, {i // 2}), color=BLUE, radius=0.1)\n"
            self.create_object(f"{word}_point", "dot", point_code)
        
        # Draw relationships
        axes_anim = "        self.play(Create(ax))\n"
        for word in words:
            axes_anim += f"        self.play(FadeIn({word}_point))\n"
        self.add_animation_code(axes_anim)

class ConvolutionFiltersTemplate(CompositionAwareTemplate):
    """Template for visualizing convolutional filters in CNNs."""
    def compose(self) -> None:
        # Input image
        img_code = "        img = Rectangle(width=2, height=2, color=BLUE_A, fill_opacity=0.3)\n"
        self.create_object("image", "rectangle", img_code)
        
        # Convolution filter
        filter_code = "        kernel = Rectangle(width=0.5, height=0.5, color=GOLD, fill_opacity=0.5)\n"
        self.create_object("kernel", "rectangle", filter_code)
        
        # Output feature map
        output_code = "        output = Rectangle(width=1.5, height=1.5, color=GREEN, fill_opacity=0.2)\n"
        self.create_object("output", "rectangle", output_code)
        
        anim_code = "        self.play(Create(img), Create(kernel))\n        self.wait(1)\n        self.play(Create(output))\n"
        self.add_animation_code(anim_code)
