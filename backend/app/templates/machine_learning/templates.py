from typing import Any, Dict, List

from app.templates.base import BaseTemplate
from app.templates.composition import CompositionAwareTemplate, CompositionContext


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


class MnistRecognitionTemplate(BaseTemplate):
    """Template for explaining MNIST digit recognition end-to-end."""

    def generate_construct_code(self) -> str:
        sample_digits = self.parameters.get("sample_digits", [3, 8, 1, 6])
        probabilities = self.parameters.get(
            "probabilities",
            [0.02, 0.03, 0.01, 0.06, 0.02, 0.04, 0.05, 0.07, 0.65, 0.05],
        )

        try:
            probs = [float(p) for p in probabilities][:10]
        except Exception:
            probs = [0.02, 0.03, 0.01, 0.06, 0.02, 0.04, 0.05, 0.07, 0.65, 0.05]

        if len(probs) < 10:
            probs += [0.0] * (10 - len(probs))

        max_prob = max(probs) if max(probs) > 0 else 1.0
        predicted_digit = int(max(range(len(probs)), key=lambda i: probs[i]))
        confidence_pct = round(probs[predicted_digit] * 100, 1)

        code = f"        # MNIST Recognition Pipeline\n"
        code += f"        title = Text('How MNIST Digit Recognition Works', font_size=36, color=YELLOW)\n"
        code += f"        title.to_edge(UP)\n"
        code += f"        self.play(Write(title))\n"
        code += f"\n"

        code += f"        sample_digits = {sample_digits}\n"
        code += f"        samples = VGroup()\n"
        code += f"        for d in sample_digits:\n"
        code += f"            frame = Square(side_length=0.9, color=BLUE_C, fill_opacity=0.15)\n"
        code += f"            digit = Text(str(d), font_size=32).move_to(frame.get_center())\n"
        code += f"            tile = VGroup(frame, digit)\n"
        code += f"            samples.add(tile)\n"
        code += f"        samples.arrange(RIGHT, buff=0.2).to_edge(LEFT, buff=0.7).shift(UP*0.4)\n"
        code += f"        input_label = Text('Input: 28x28 grayscale digits', font_size=22).next_to(samples, DOWN, buff=0.25)\n"
        code += f"        self.play(FadeIn(samples), Write(input_label))\n"
        code += f"        self.play(Indicate(samples[1]))\n"
        code += f"\n"

        code += f"        cnn_block = RoundedRectangle(width=3.8, height=1.4, corner_radius=0.15, color=TEAL, fill_opacity=0.15)\n"
        code += f"        cnn_block.move_to([-0.4, 0.5, 0])\n"
        code += f"        cnn_text = Text('Convolution + ReLU + Pooling', font_size=24).move_to(cnn_block.get_center())\n"
        code += f"        arrow_in = Arrow(samples.get_right() + RIGHT*0.2, cnn_block.get_left() + LEFT*0.05, buff=0.05, color=BLUE_B)\n"
        code += f"        self.play(GrowArrow(arrow_in), Create(cnn_block), Write(cnn_text))\n"
        code += f"\n"

        code += f"        feature_heights = [0.8, 1.4, 1.0, 1.8, 1.2, 0.9]\n"
        code += f"        feature_maps = VGroup(*[Rectangle(width=0.2, height=h, color=GREEN, fill_opacity=0.55) for h in feature_heights])\n"
        code += (
            f"        feature_maps.arrange(RIGHT, buff=0.08).next_to(cnn_block, RIGHT, buff=0.7)\n"
        )
        code += f"        feature_label = Text('Extracted features', font_size=20).next_to(feature_maps, DOWN, buff=0.2)\n"
        code += f"        arrow_mid = Arrow(cnn_block.get_right() + RIGHT*0.05, feature_maps.get_left() + LEFT*0.05, buff=0.05, color=GREEN_B)\n"
        code += f"        self.play(\n"
        code += f"            GrowArrow(arrow_mid),\n"
        code += f"            LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in feature_maps], lag_ratio=0.12),\n"
        code += f"            Write(feature_label)\n"
        code += f"        )\n"
        code += f"\n"

        code += f"        classifier = RoundedRectangle(width=2.6, height=1.0, corner_radius=0.12, color=PURPLE, fill_opacity=0.12)\n"
        code += f"        classifier.next_to(feature_maps, RIGHT, buff=0.6)\n"
        code += f"        classifier_text = Text('Dense + Softmax', font_size=22).move_to(classifier.get_center())\n"
        code += f"        arrow_cls = Arrow(feature_maps.get_right() + RIGHT*0.05, classifier.get_left() + LEFT*0.05, buff=0.05, color=PURPLE_B)\n"
        code += (
            f"        self.play(GrowArrow(arrow_cls), Create(classifier), Write(classifier_text))\n"
        )
        code += f"\n"

        code += f"        probs = {probs}\n"
        code += f"        max_prob = {max_prob}\n"
        code += f"        bars = VGroup()\n"
        code += f"        digits = VGroup()\n"
        code += f"        for i, p in enumerate(probs):\n"
        code += f"            h = 0.3 + 2.1 * (p / max_prob)\n"
        code += (
            f"            bar = Rectangle(width=0.33, height=h, color=BLUE_D, fill_opacity=0.75)\n"
        )
        code += f"            bars.add(bar)\n"
        code += f"            digits.add(Text(str(i), font_size=16))\n"
        code += f"        bars.arrange(RIGHT, buff=0.06, aligned_edge=DOWN).to_edge(RIGHT, buff=0.45).shift(DOWN*0.2)\n"
        code += f"        for label, bar in zip(digits, bars):\n"
        code += f"            label.next_to(bar, DOWN, buff=0.06)\n"
        code += f"        prob_label = Text('Class probabilities', font_size=20).next_to(bars, UP, buff=0.18)\n"
        code += f"        arrow_out = Arrow(classifier.get_right() + RIGHT*0.05, bars.get_left() + LEFT*0.05, buff=0.05, color=BLUE_A)\n"
        code += f"        self.play(GrowArrow(arrow_out), Create(bars), Write(digits), Write(prob_label))\n"
        code += f"\n"

        code += f"        pred = {predicted_digit}\n"
        code += f"        confidence = {confidence_pct}\n"
        code += f"        self.play(bars[pred].animate.set_color(YELLOW), digits[pred].animate.set_color(YELLOW))\n"
        code += f"        pred_text = Text(f'Prediction: {{pred}}', font_size=30, color=YELLOW).to_edge(DOWN).shift(LEFT*2.0)\n"
        code += f"        conf_text = Text(f'Confidence: {{confidence}}%', font_size=24, color=WHITE).next_to(pred_text, RIGHT, buff=0.5)\n"
        code += f"        self.play(Write(pred_text), Write(conf_text))\n"
        code += f"        self.wait(2)\n"
        return code


class TransformerAttentionTemplate(BaseTemplate):
    """Template for 3Blue1Brown style Transformer Attention mechanisms."""

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

        sentence = str(
            self.parameters.get("sentence", "The cat chased the mouse because it was hungry.")
        ).strip()

        tokens_raw = self.parameters.get("tokens")
        if isinstance(tokens_raw, list) and tokens_raw:
            tokens = [str(t).strip() for t in tokens_raw if str(t).strip()]
        else:
            cleaned = (
                sentence.replace(",", " ,")
                .replace(".", " .")
                .replace("?", " ?")
                .replace("!", " !")
            )
            tokens = [t for t in cleaned.split() if t]

        if not tokens:
            tokens = ["The", "cat", "was", "hungry", "."]
        tokens = [t[:12] for t in tokens[:8]]

        requested_focus = str(self.parameters.get("focus_token", "it")).strip().lower()
        normalized = [t.lower().strip(".,!?") for t in tokens]

        if requested_focus in normalized:
            focus_idx = normalized.index(requested_focus)
        else:
            pronouns = {"it", "he", "she", "they", "this", "that"}
            focus_idx = next((i for i, w in enumerate(normalized) if w in pronouns), len(tokens) // 2)

        weights_raw = self.parameters.get("attention_weights")
        if isinstance(weights_raw, list) and len(weights_raw) == len(tokens):
            try:
                weights = [max(0.01, float(w)) for w in weights_raw]
            except (TypeError, ValueError):
                weights = [0.08] * len(tokens)
        else:
            weights = [0.08] * len(tokens)
            if focus_idx > 0:
                weights[focus_idx - 1] += 0.24
            if focus_idx + 1 < len(tokens):
                weights[focus_idx + 1] += 0.10
            for i, tok in enumerate(normalized):
                if tok in {"cat", "dog", "animal", "student", "mouse", "model"}:
                    weights[i] += 0.12
                if tok in {"hungry", "tired", "sleepy", "sick", "because"}:
                    weights[i] += 0.08
            weights[focus_idx] += 0.16

        total = sum(weights) if sum(weights) > 0 else 1.0
        weights = [round(w / total, 2) for w in weights]

        scored_ids = sorted(range(len(tokens)), key=lambda i: weights[i], reverse=True)
        top_terms = [tokens[i].strip(".,!?") for i in scored_ids if tokens[i].strip(".,!?")][:2]
        if not top_terms:
            top_terms = [tokens[focus_idx]]

        focus_word = tokens[focus_idx]
        context_text = f"Context for '{focus_word}' emphasizes: " + " + ".join(top_terms)

        code = "        # Sentence-level Self-Attention Explanation\n"
        code += f"        detail_level = {repr(detail_level)}\n"
        code += f"        tokens = {tokens}\n"
        code += f"        weights = {weights}\n"
        code += f"        focus_idx = {focus_idx}\n"
        code += "\n"
        code += "        title = Text('Self-Attention on a Simple Sentence', font_size=34, color=YELLOW).to_edge(UP)\n"
        code += f"        sentence_text = Text({repr(sentence[:96])}, font_size=24, color=WHITE).next_to(title, DOWN, buff=0.25)\n"
        code += f"        self.play(Write(title), run_time={1.0 * pace_scale:.2f})\n"
        code += f"        self.play(FadeIn(sentence_text), run_time={0.8 * pace_scale:.2f})\n"
        code += "\n"
        code += "        token_boxes = VGroup(*[RoundedRectangle(width=1.35, height=0.72, corner_radius=0.08, color=TEAL_A, fill_opacity=0.18) for _ in tokens])\n"
        code += "        token_boxes.arrange(RIGHT, buff=0.18).next_to(sentence_text, DOWN, buff=0.55)\n"
        code += "        if token_boxes.width > 12:\n"
        code += "            token_boxes.scale_to_fit_width(12)\n"
        code += "        token_labels = VGroup(*[Text(tok, font_size=22 if len(tokens) <= 6 else 18) for tok in tokens])\n"
        code += "        for box, label in zip(token_boxes, token_labels):\n"
        code += "            label.move_to(box.get_center())\n"
        code += f"        self.play(Create(token_boxes), Write(token_labels), run_time={1.0 * pace_scale:.2f})\n"
        code += "\n"
        code += "        query_box = SurroundingRectangle(token_boxes[focus_idx], color=YELLOW, buff=0.06)\n"
        code += "        query_label = Text(f'Query token: {tokens[focus_idx]}', font_size=22, color=YELLOW).next_to(token_boxes, DOWN, buff=0.28)\n"
        code += f"        self.play(Create(query_box), Write(query_label), run_time={0.85 * pace_scale:.2f})\n"
        code += "\n"
        code += "        attention_arcs = VGroup()\n"
        code += "        attention_scores = VGroup()\n"
        code += "        for i, w in enumerate(weights):\n"
        code += "            if i == focus_idx:\n"
        code += "                self_score = Text(f'{w:.2f}', font_size=16, color=YELLOW).next_to(token_boxes[i], UP, buff=0.08)\n"
        code += "                attention_scores.add(self_score)\n"
        code += "                continue\n"
        code += "            start = token_boxes[focus_idx].get_bottom()\n"
        code += "            end = token_boxes[i].get_bottom()\n"
        code += "            angle = -0.85 if i < focus_idx else 0.85\n"
        code += "            arc = ArcBetweenPoints(start, end, angle=angle, color=GOLD)\n"
        code += "            arc.set_stroke(width=1.5 + 9.0 * w, opacity=0.35 + 0.55 * w)\n"
        code += "            score = Text(f'{w:.2f}', font_size=15, color=GOLD).move_to(arc.point_from_proportion(0.5) + (UP*0.18 if i < focus_idx else DOWN*0.18))\n"
        code += "            attention_arcs.add(arc)\n"
        code += "            attention_scores.add(score)\n"
        code += f"        self.play(LaggedStart(*[Create(a) for a in attention_arcs], lag_ratio=0.12), run_time={1.2 * pace_scale:.2f})\n"
        code += f"        self.play(FadeIn(attention_scores), run_time={0.8 * pace_scale:.2f})\n"
        code += "\n"
        code += "        context_box = RoundedRectangle(width=4.6, height=1.0, corner_radius=0.12, color=GREEN, fill_opacity=0.12).next_to(query_label, DOWN, buff=0.35)\n"
        code += f"        context_caption = Text({repr(context_text)}, font_size=20, color=GREEN).move_to(context_box.get_center())\n"
        code += f"        self.play(Create(context_box), Write(context_caption), run_time={0.95 * pace_scale:.2f})\n"
        code += "\n"
        code += "        output_box = RoundedRectangle(width=3.8, height=0.9, corner_radius=0.1, color=BLUE_C, fill_opacity=0.15).next_to(context_box, DOWN, buff=0.3)\n"
        code += "        output_text = Text(f'Updated representation of " + "{tokens[focus_idx]}" + "', font_size=20, color=BLUE_C).move_to(output_box.get_center())\n"
        code += f"        self.play(TransformFromCopy(token_boxes[focus_idx], output_box), Write(output_text), run_time={0.9 * pace_scale:.2f})\n"
        code += "\n"
        code += "        if detail_level == 'advanced':\n"
        code += "            eq = MathTex(r'\\alpha_{i,j}=\\mathrm{softmax}\\left(\\frac{Q_i K_j^T}{\\sqrt{d_k}}\\right)', color=BLUE_B).scale(0.75).to_edge(DOWN)\n"
        code += f"            self.play(Write(eq), run_time={0.85 * pace_scale:.2f})\n"
        code += "\n"
        code += "        takeaway = Text('Each word attends to relevant words in the same sentence.', font_size=22).to_edge(DOWN)\n"
        code += f"        self.play(Write(takeaway), run_time={0.9 * pace_scale:.2f})\n"
        code += f"        self.wait({1.8 * pace_scale:.2f})\n"
        return code


# Phase 2: Advanced Machine Learning Templates


class BackpropagationTemplate(CompositionAwareTemplate):
    """Template for visualizing backpropagation through a network."""

    def compose(self, context: "CompositionContext") -> None:
        # Simple network: input -> hidden -> output
        input_code = "        input_layer = VGroup(*[Circle(0.2, color=BLUE) for _ in range(3)])\n"
        context.add_obj("input_layer", "layer", input_code)

        hidden_code = (
            "        hidden_layer = VGroup(*[Circle(0.2, color=GREEN) for _ in range(4)])\n"
        )
        context.add_obj("hidden_layer", "layer", hidden_code)

        output_code = "        output_layer = VGroup(*[Circle(0.2, color=RED) for _ in range(2)])\n"
        context.add_obj("output_layer", "layer", output_code)

        # Forward pass
        forward_code = "        # Forward Pass: Input -> Hidden -> Output\n        self.play(Create(input_layer), Create(hidden_layer), Create(output_layer))\n"
        context.add_anim(forward_code)

        # Backward pass
        backward_code = "        # Backward Pass: Gradient flow\n        self.wait(1)\n"
        context.add_anim(backward_code)


class EmbeddingSpaceTemplate(CompositionAwareTemplate):
    """Template for visualizing word/token embeddings in vector space."""

    def compose(self, context: "CompositionContext") -> None:
        # 2D or 3D embedding space
        axes_code = "        ax = Axes(x_range=[-2, 2], y_range=[-2, 2])\n"
        context.add_obj("axes", "axes", axes_code)

        # Words as points
        words = self.parameters.get("words", ["king", "queen", "man", "woman"])

        # Create word points
        for i, word in enumerate(words):
            point_code = (
                f"        {word}_point = Dot(ax.c2p({i % 2}, {i // 2}), color=BLUE, radius=0.1)\n"
            )
            context.add_obj(f"{word}_point", "dot", point_code)

        # Draw relationships
        axes_anim = "        self.play(Create(ax))\n"
        for word in words:
            axes_anim += f"        self.play(FadeIn({word}_point))\n"
        context.add_anim(axes_anim)


class ConvolutionFiltersTemplate(BaseTemplate):
    """Template for visualizing convolution, pooling, and classification in a CNN."""

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

        probabilities = self.parameters.get(
            "probabilities",
            [0.03, 0.02, 0.01, 0.04, 0.03, 0.05, 0.06, 0.08, 0.62, 0.06],
        )
        try:
            probs = [float(p) for p in probabilities][:10]
        except Exception:
            probs = [0.03, 0.02, 0.01, 0.04, 0.03, 0.05, 0.06, 0.08, 0.62, 0.06]

        if len(probs) < 10:
            probs += [0.0] * (10 - len(probs))

        max_prob = max(probs) if max(probs) > 0 else 1.0
        predicted_class = int(max(range(len(probs)), key=lambda i: probs[i]))

        code = "        # CNN Pipeline: Convolution -> Pooling -> Classification\n"
        code += f"        detail_level = {repr(detail_level)}\n"
        code += "        title = Text('CNN: Convolution, Pooling, Classification', font_size=34, color=YELLOW).to_edge(UP)\n"
        code += f"        self.play(Write(title), run_time={1.1 * pace_scale:.2f})\n"
        code += "\n"

        code += "        input_grid = VGroup(*[Square(side_length=0.18, color=BLUE_D, stroke_width=1, fill_opacity=0.15) for _ in range(16)])\n"
        code += "        input_grid.arrange_in_grid(rows=4, cols=4, buff=0.03).shift(LEFT*5 + DOWN*0.15)\n"
        code += "        input_label = Text('Input image', font_size=20).next_to(input_grid, DOWN, buff=0.15)\n"
        code += "\n"

        code += "        kernel = Square(side_length=0.42, color=GOLD, fill_opacity=0.25)\n"
        code += "        kernel.move_to(input_grid.get_corner(UL) + RIGHT*0.21 + DOWN*0.21)\n"
        code += "        kernel_label = Text('Kernel', font_size=18, color=GOLD).next_to(kernel, UP, buff=0.08)\n"
        code += "\n"

        code += f"        self.play(FadeIn(input_grid), Write(input_label), run_time={1.0 * pace_scale:.2f})\n"
        code += f"        self.play(Create(kernel), FadeIn(kernel_label), run_time={0.9 * pace_scale:.2f})\n"
        code += f"        self.play(kernel.animate.shift(RIGHT*0.21), run_time={0.45 * pace_scale:.2f})\n"
        code += f"        self.play(kernel.animate.shift(DOWN*0.21), run_time={0.45 * pace_scale:.2f})\n"
        code += f"        self.play(kernel.animate.shift(RIGHT*0.21), run_time={0.45 * pace_scale:.2f})\n"
        code += "\n"

        code += "        conv_arrow = Arrow(input_grid.get_right() + RIGHT*0.15, RIGHT*1.35 + DOWN*0.05, buff=0.05, color=GREEN_B)\n"
        code += "        feature_heights = [0.7, 1.1, 0.9, 1.4, 1.0, 0.8]\n"
        code += "        feature_map = VGroup(*[Rectangle(width=0.2, height=h, color=GREEN, fill_opacity=0.6) for h in feature_heights])\n"
        code += "        feature_map.arrange(RIGHT, buff=0.08).shift(LEFT*1.8 + DOWN*0.1)\n"
        code += "        conv_label = Text('Convolution -> Feature Map', font_size=20, color=GREEN).next_to(feature_map, DOWN, buff=0.15)\n"
        code += "\n"
        code += f"        self.play(GrowArrow(conv_arrow), LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in feature_map], lag_ratio=0.12), Write(conv_label), run_time={1.1 * pace_scale:.2f})\n"
        code += "\n"

        code += "        pool_arrow = Arrow(feature_map.get_right() + RIGHT*0.15, RIGHT*3.3 + DOWN*0.05, buff=0.05, color=BLUE_B)\n"
        code += "        pooled = VGroup(*[Rectangle(width=0.24, height=h, color=BLUE_C, fill_opacity=0.7) for h in [1.0, 1.35, 0.95]])\n"
        code += "        pooled.arrange(RIGHT, buff=0.1).shift(RIGHT*1.0 + DOWN*0.1)\n"
        code += "        pool_label = Text('Pooling', font_size=20, color=BLUE_C).next_to(pooled, DOWN, buff=0.15)\n"
        code += "\n"
        code += f"        self.play(GrowArrow(pool_arrow), LaggedStart(*[Create(p) for p in pooled], lag_ratio=0.15), Write(pool_label), run_time={1.0 * pace_scale:.2f})\n"
        code += "\n"

        code += "        cls_arrow = Arrow(pooled.get_right() + RIGHT*0.15, RIGHT*5.35 + DOWN*0.05, buff=0.05, color=PURPLE_B)\n"
        code += "        classifier = RoundedRectangle(width=2.2, height=0.95, corner_radius=0.12, color=PURPLE, fill_opacity=0.12).shift(RIGHT*3.35 + DOWN*0.05)\n"
        code += "        cls_text = Text('Dense + Softmax', font_size=20, color=PURPLE).move_to(classifier.get_center())\n"
        code += "\n"
        code += f"        self.play(GrowArrow(cls_arrow), Create(classifier), Write(cls_text), run_time={0.95 * pace_scale:.2f})\n"
        code += "\n"

        code += "        if detail_level == 'advanced':\n"
        code += (
            "            receptive = SurroundingRectangle(feature_map, color=YELLOW, buff=0.12)\n"
        )
        code += "            receptive_text = Text('Receptive fields capture local patterns', font_size=18, color=YELLOW).next_to(feature_map, UP, buff=0.15)\n"
        code += f"            self.play(Create(receptive), Write(receptive_text), run_time={1.0 * pace_scale:.2f})\n"
        code += f"            self.play(FadeOut(receptive), FadeOut(receptive_text), run_time={0.7 * pace_scale:.2f})\n"
        code += "\n"

        code += f"        probs = {probs}\n"
        code += f"        max_prob = {max_prob}\n"
        code += "        bars = VGroup()\n"
        code += "        digits = VGroup()\n"
        code += "        for i, p in enumerate(probs):\n"
        code += "            h = 0.25 + 1.7 * (p / max_prob)\n"
        code += "            bar = Rectangle(width=0.18, height=h, color=TEAL, fill_opacity=0.75)\n"
        code += "            bars.add(bar)\n"
        code += "            digits.add(Text(str(i), font_size=14))\n"
        code += "        bars.arrange(RIGHT, buff=0.03, aligned_edge=DOWN).to_edge(RIGHT, buff=0.35).shift(DOWN*0.2)\n"
        code += "        for d, b in zip(digits, bars):\n"
        code += "            d.next_to(b, DOWN, buff=0.04)\n"
        code += "        prob_label = Text('Classification probabilities', font_size=18).next_to(bars, UP, buff=0.12)\n"
        code += "\n"
        code += f"        self.play(Create(bars), Write(digits), Write(prob_label), run_time={1.0 * pace_scale:.2f})\n"
        code += f"        pred_idx = {predicted_class}\n"
        code += f"        self.play(bars[pred_idx].animate.set_color(YELLOW), digits[pred_idx].animate.set_color(YELLOW), run_time={0.85 * pace_scale:.2f})\n"
        code += "        pred_text = Text(f'Predicted class: {pred_idx}', font_size=24, color=YELLOW).to_edge(DOWN)\n"
        code += f"        self.play(Write(pred_text), run_time={0.95 * pace_scale:.2f})\n"
        code += f"        self.wait({2.0 * pace_scale:.2f})\n"
        return code
