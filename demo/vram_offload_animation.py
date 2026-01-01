"""
VRAM Layer Offloading Animation for VibeVoice

Demonstrates the layer offloading mechanism during inference:
- Layers move from CPU to GPU before computation
- Computation happens on GPU
- Layers move back to CPU after computation
- Next layer is loaded while current layer is processed

Usage:
    # English version (default)
    manim -pql vram_offload_animation.py LayerOffloadingDemo

    # Chinese version
    LANG=zh manim -pql vram_offload_animation.py LayerOffloadingDemo

    # High quality
    manim -pqh vram_offload_animation.py LayerOffloadingDemo

Requirements:
    pip install manim
"""

import os

from manim import (
    Scene, VGroup, Rectangle, RoundedRectangle, Text, Arrow, DashedVMobject,
    Create, Write, FadeIn, FadeOut, Transform,
    UP, DOWN, LEFT, RIGHT, ORIGIN,
    GREEN, BLUE, YELLOW, ORANGE, WHITE, GRAY,
    BLUE_C, GREEN_C, RED_C,
)

# Language configuration: "en" for English, "zh" for Chinese
# Can be set via environment variable: LANG=zh manim ...
LANGUAGE = os.environ.get("LANG", "en")
if LANGUAGE.startswith("zh"):
    LANGUAGE = "zh"
else:
    LANGUAGE = "en"

# Translation dictionary
TRANSLATIONS = {
    "en": {
        "title": "VibeVoiceFusion VRAM Layer Offloading Demonstration",
        "gpu_vram": "GPU VRAM",
        "cpu_ram": "CPU RAM",
        "gpu_info": "Fast compute\n~16 GB/s bandwidth",
        "cpu_info": "Staging buffers\n(Pinned memory)",
        "pcie_transfer": "PCIe Transfer",
        "exchange_slot": "Exchange Slot",
        "gpu_resident": "GPU-Resident (Layers 8-27)",
        "offloaded": "Offloaded (Layers 0-7)",
        "initial_state": "20 layers stay on GPU | 8 layers offloaded to CPU | 1 exchange slot",
        "phase1": "Phase 1: Processing Offloaded Layers (0-7)",
        "phase2": "Phase 2: Processing GPU-Resident Layers (8-27)",
        "step1_load": "Step 1: Loading Layer {idx} → Exchange Slot...",
        "step2_compute": "Step 2: Computing Layer {idx} on GPU...",
        "step3_offload": "Step 3: Offloading Layer {idx} back to CPU...",
        "fast_forward": "Layers 3-7: Same process (CPU → Exchange Slot → CPU)",
        "gpu_direct": "GPU-resident layers: No transfer needed - Direct compute!",
        "token_generated": "Token generated! Repeat for next token...",
        "summary_title": "Summary: Layer Offloading Flow",
        "for_each_token": "For each token generation:",
        "offloaded_layers": "Offloaded Layers (0-7):",
        "offload_step1": "  1. Load from CPU → GPU (PCIe transfer)",
        "offload_step2": "  2. Compute on GPU",
        "offload_step3": "  3. Offload GPU → CPU (PCIe transfer)",
        "gpu_layers": "GPU-Resident Layers (8-27):",
        "gpu_step1": "  1. Compute directly on GPU (no transfer)",
        "benefits": "Benefits:",
        "benefit1": "  - VRAM reduced from 14GB to 5-7GB",
        "benefit2": "  - Can run on smaller GPUs (RTX 3060, 4070)",
        "benefit3": "  - Trade-off: ~1.3s per token (vs 0.2s baseline)",
        "layer": "Layer {idx}",
        # SimpleLayerFlow
        "simple_title": "Layer Offloading: One Token Generation",
        "gpu": "GPU",
        "cpu": "CPU",
        "ready": "Ready to process token",
        "loading_layer": "Loading Layer {idx} → Exchange Slot...",
        "computing_layer": "Computing Layer {idx}...",
        "offloading_layer": "Offloading Layer {idx} back to CPU...",
        "processing_gpu": "Processing GPU-resident layers (no transfer needed)...",
        "token_done": "Token Generated!",
        # InferenceTimeline
        "timeline_title": "Inference Timeline: Layer Processing Order",
        "offloaded_layers_label": "Offloaded Layers (0-7)",
        "gpu_layers_label": "GPU Layers (8-27)",
        "cpu_to_gpu": "CPU→GPU",
        "compute": "Compute",
        "gpu_to_cpu": "GPU→CPU",
        "gpu_direct_label": "GPU Direct",
        "time": "Time →",
        "overhead": "Offloaded layers: Transfer overhead per layer (~70ms each)",
        "fast": "GPU layers: Direct compute, no transfer (~1ms each)",
    },
    "zh": {
        "title": "VibeVoiceFusion 显存层卸载机制演示",
        "gpu_vram": "GPU 显存",
        "cpu_ram": "CPU 内存",
        "gpu_info": "高速计算\n~16 GB/s 带宽",
        "cpu_info": "暂存缓冲区\n(锁页内存)",
        "pcie_transfer": "PCIe 传输",
        "exchange_slot": "交换槽位",
        "gpu_resident": "GPU常驻层 (层 8-27)",
        "offloaded": "卸载层 (层 0-7)",
        "initial_state": "20层常驻GPU | 8层卸载至CPU | 1个交换槽位",
        "phase1": "阶段一：处理卸载层 (0-7)",
        "phase2": "阶段二：处理GPU常驻层 (8-27)",
        "step1_load": "步骤1：加载层 {idx} → 交换槽位...",
        "step2_compute": "步骤2：在GPU上计算层 {idx}...",
        "step3_offload": "步骤3：将层 {idx} 卸载回CPU...",
        "fast_forward": "层 3-7：相同流程 (CPU → 交换槽位 → CPU)",
        "gpu_direct": "GPU常驻层：无需传输 - 直接计算！",
        "token_generated": "Token生成完成！重复处理下一个Token...",
        "summary_title": "总结：层卸载流程",
        "for_each_token": "每个Token生成过程：",
        "offloaded_layers": "卸载层 (0-7)：",
        "offload_step1": "  1. 从CPU加载到GPU (PCIe传输)",
        "offload_step2": "  2. 在GPU上计算",
        "offload_step3": "  3. 从GPU卸载回CPU (PCIe传输)",
        "gpu_layers": "GPU常驻层 (8-27)：",
        "gpu_step1": "  1. 直接在GPU上计算 (无需传输)",
        "benefits": "优势：",
        "benefit1": "  - 显存从14GB降至5-7GB",
        "benefit2": "  - 可在小显存GPU上运行 (RTX 3060, 4070)",
        "benefit3": "  - 代价：每Token约1.3秒 (基准0.2秒)",
        "layer": "层 {idx}",
        # SimpleLayerFlow
        "simple_title": "层卸载：单Token生成过程",
        "gpu": "GPU",
        "cpu": "CPU",
        "ready": "准备处理Token",
        "loading_layer": "加载层 {idx} → 交换槽位...",
        "computing_layer": "计算层 {idx}...",
        "offloading_layer": "卸载层 {idx} 回CPU...",
        "processing_gpu": "处理GPU常驻层 (无需传输)...",
        "token_done": "Token生成完成！",
        # InferenceTimeline
        "timeline_title": "推理时间线：层处理顺序",
        "offloaded_layers_label": "卸载层 (0-7)",
        "gpu_layers_label": "GPU层 (8-27)",
        "cpu_to_gpu": "CPU→GPU",
        "compute": "计算",
        "gpu_to_cpu": "GPU→CPU",
        "gpu_direct_label": "GPU直接",
        "time": "时间 →",
        "overhead": "卸载层：每层传输开销约70ms",
        "fast": "GPU层：直接计算，无传输 (约1ms/层)",
    },
}


def t(key: str, **kwargs) -> str:
    """Get translated text for the current language."""
    text = TRANSLATIONS.get(LANGUAGE, TRANSLATIONS["en"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


class LayerOffloadingDemo(Scene):
    """
    Main animation demonstrating VRAM layer offloading during inference.
    Shows how layers move between CPU and GPU during token generation.
    """

    def construct(self):
        # Title
        self.title = Text(t("title"), font_size=36)
        self.title.to_edge(UP, buff=0.3)
        self.play(Write(self.title))

        # Create memory regions
        gpu_region, cpu_region, pcie_arrow, pcie_label = self.create_memory_regions()

        # Store for later cleanup
        self.gpu_region = gpu_region
        self.cpu_region = cpu_region
        self.pcie_arrow = pcie_arrow
        self.pcie_label = pcie_label

        # Create all 28 layers
        all_layers = self.create_layers()
        self.all_layers = all_layers

        # Initial state: show which layers are where
        self.show_initial_state(all_layers, gpu_region, cpu_region)

        # Demonstrate inference flow
        self.demonstrate_inference_flow(all_layers, gpu_region, cpu_region, pcie_arrow)

        # Final summary
        self.show_summary()

    def create_memory_regions(self):
        """Create GPU VRAM and CPU RAM regions with PCIe connection"""
        # GPU VRAM (right side, larger)
        gpu_box = RoundedRectangle(
            corner_radius=0.15,
            width=6.5,
            height=4,
            color=ORANGE,
            fill_opacity=0.1,
            stroke_width=2,
        )
        gpu_box.shift(RIGHT * 3 + DOWN * 0.3)

        gpu_label = Text(t("gpu_vram"), font_size=24, color=ORANGE)
        gpu_label.next_to(gpu_box, UP, buff=0.1)

        gpu_info = Text(t("gpu_info"), font_size=14, color=GRAY)
        gpu_info.next_to(gpu_box, DOWN, buff=0.1)

        # CPU RAM (left side)
        cpu_box = RoundedRectangle(
            corner_radius=0.15,
            width=4,
            height=4,
            color=BLUE,
            fill_opacity=0.1,
            stroke_width=2,
        )
        cpu_box.shift(LEFT * 4.5 + DOWN * 0.3)

        cpu_label = Text(t("cpu_ram"), font_size=24, color=BLUE)
        cpu_label.next_to(cpu_box, UP, buff=0.1)

        cpu_info = Text(t("cpu_info"), font_size=14, color=GRAY)
        cpu_info.next_to(cpu_box, DOWN, buff=0.1)

        # PCIe connection
        pcie_arrow = Arrow(
            cpu_box.get_right() + RIGHT * 0.1,
            gpu_box.get_left() + LEFT * 0.1,
            color=YELLOW,
            stroke_width=4,
            buff=0,
            max_tip_length_to_length_ratio=0.1,
        )
        pcie_label = Text(t("pcie_transfer"), font_size=16, color=YELLOW)
        pcie_label.next_to(pcie_arrow, UP, buff=0.05)

        # Add all elements
        self.play(
            Create(gpu_box), Create(cpu_box),
            Write(gpu_label), Write(cpu_label),
        )
        self.play(
            Write(gpu_info), Write(cpu_info),
            Create(pcie_arrow), Write(pcie_label),
        )

        gpu_region = VGroup(gpu_box, gpu_label, gpu_info)
        cpu_region = VGroup(cpu_box, cpu_label, cpu_info)

        return gpu_region, cpu_region, pcie_arrow, pcie_label

    def create_layers(self):
        """Create 28 transformer layers"""
        layers = []

        for i in range(28):
            # Layer rectangle
            layer = RoundedRectangle(
                corner_radius=0.05,
                width=3.0,
                height=0.35,
                stroke_width=1.5,
            )

            # Layer label
            label = Text(t("layer", idx=i), font_size=12)
            label.move_to(layer.get_center())

            layer_group = VGroup(layer, label)
            layer_group.layer_idx = i

            layers.append(layer_group)

        return layers

    def show_initial_state(self, all_layers, gpu_region, cpu_region):
        """Show initial state: 20 layers on GPU (2 columns), 8 on CPU, plus exchange slot"""
        gpu_box = gpu_region[0]
        cpu_box = cpu_region[0]

        # Create exchangeable layer slot (dashed border) at top of GPU
        exchange_slot = RoundedRectangle(
            corner_radius=0.05,
            width=2.8,
            height=0.4,
            stroke_color=YELLOW,
            stroke_width=2,
            fill_opacity=0.1,
            fill_color=YELLOW,
        )
        # Make it dashed
        dashed_slot = DashedVMobject(exchange_slot, num_dashes=20)
        dashed_slot.move_to(gpu_box.get_top() + DOWN * 0.5)

        slot_label = Text(t("exchange_slot"), font_size=12, color=YELLOW)
        slot_label.next_to(dashed_slot, UP, buff=0.05)

        self.exchange_slot = dashed_slot  # Store for later use
        self.exchange_slot_pos = dashed_slot.get_center()
        self.slot_label = slot_label

        # Position GPU-resident layers (8-27) on GPU in TWO COLUMNS
        gpu_layers = all_layers[8:28]
        for layer in gpu_layers:
            layer[0].set_fill(GREEN, opacity=0.7)
            layer[0].set_stroke(GREEN)
            layer[1].set_color(WHITE)
            layer.scale(0.7)  # Make layers smaller to fit

        # Split into two columns (10 layers each)
        left_column = VGroup(*gpu_layers[0:10])
        right_column = VGroup(*gpu_layers[10:20])

        left_column.arrange(DOWN, buff=0.02)
        right_column.arrange(DOWN, buff=0.02)

        gpu_layers_group = VGroup(left_column, right_column)
        gpu_layers_group.arrange(RIGHT, buff=0.15)
        gpu_layers_group.move_to(gpu_box.get_center() + DOWN * 0.3)

        # Position offloaded layers (0-7) on CPU
        cpu_layers = all_layers[0:8]
        for layer in cpu_layers:
            layer[0].set_fill(BLUE_C, opacity=0.6)
            layer[0].set_stroke(BLUE_C)
            layer[1].set_color(WHITE)
            layer.scale(0.85)

        cpu_group = VGroup(*cpu_layers)
        cpu_group.arrange(DOWN, buff=0.04)
        cpu_group.move_to(cpu_box.get_center())

        # Legend
        legend = VGroup(
            VGroup(
                Rectangle(width=0.4, height=0.2, fill_color=GREEN, fill_opacity=0.7, stroke_width=0),
                Text(t("gpu_resident"), font_size=14),
            ).arrange(RIGHT, buff=0.15),
            VGroup(
                Rectangle(width=0.4, height=0.2, fill_color=BLUE_C, fill_opacity=0.6, stroke_width=0),
                Text(t("offloaded"), font_size=14),
            ).arrange(RIGHT, buff=0.15),
            VGroup(
                DashedVMobject(Rectangle(width=0.4, height=0.2, stroke_color=YELLOW, stroke_width=2), num_dashes=6),
                Text(t("exchange_slot"), font_size=14, color=YELLOW),
            ).arrange(RIGHT, buff=0.15),
        ).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        legend.to_corner(DOWN + LEFT, buff=0.3)
        self.legend = legend

        # Animate appearance
        self.play(
            Create(dashed_slot),
            Write(slot_label),
            run_time=0.8,
        )
        self.play(
            FadeIn(gpu_layers_group),
            FadeIn(cpu_group),
            FadeIn(legend),
            run_time=1.5,
        )

        # Explanation
        explanation = Text(
            t("initial_state"),
            font_size=18,
            color=YELLOW,
        )
        explanation.to_edge(DOWN, buff=0.1)
        self.play(Write(explanation))
        self.wait(1.5)
        self.play(FadeOut(explanation))

    def demonstrate_inference_flow(self, all_layers, gpu_region, cpu_region, pcie_arrow):
        """Demonstrate the inference flow with layer offloading"""
        # Get the exchange slot position
        exchange_slot_pos = self.exchange_slot_pos

        # Phase 1: Process offloaded layers (0-7)
        phase1_title = Text(
            t("phase1"),
            font_size=22,
            color=RED_C,
        )
        phase1_title.to_edge(DOWN, buff=0.1)
        self.play(Write(phase1_title))
        self.wait(0.5)

        # Show detailed flow for first 3 layers, then summarize
        for layer_idx in range(3):
            layer = all_layers[layer_idx]

            # Step 1: Load layer from CPU to GPU (into exchange slot)
            new_status = Text(
                t("step1_load", idx=layer_idx),
                font_size=18,
                color=BLUE,
            )
            new_status.to_edge(DOWN, buff=0.1)
            self.play(Transform(phase1_title, new_status), run_time=0.6)
            self.wait(0.5)

            # Animate layer moving to exchange slot on GPU
            layer_copy = layer.copy()
            layer_copy[0].set_fill(ORANGE, opacity=0.8)
            layer_copy[0].set_stroke(ORANGE)

            self.play(
                layer.animate.set_opacity(0.3),
                layer_copy.animate.move_to(exchange_slot_pos),
                run_time=1.2,
            )
            self.wait(0.3)

            # Step 2: Compute on GPU
            new_status = Text(
                t("step2_compute", idx=layer_idx),
                font_size=18,
                color=ORANGE,
            )
            new_status.to_edge(DOWN, buff=0.1)
            self.play(Transform(phase1_title, new_status), run_time=0.5)
            self.wait(0.4)

            # Compute animation (flash)
            self.play(
                layer_copy[0].animate.set_fill(YELLOW, opacity=1),
                run_time=0.3,
            )
            self.play(
                layer_copy[0].animate.set_fill(ORANGE, opacity=0.8),
                run_time=0.3,
            )
            self.wait(0.3)

            # Step 3: Offload back to CPU
            new_status = Text(
                t("step3_offload", idx=layer_idx),
                font_size=18,
                color=BLUE_C,
            )
            new_status.to_edge(DOWN, buff=0.1)
            self.play(Transform(phase1_title, new_status), run_time=0.5)
            self.wait(0.4)

            self.play(
                layer_copy.animate.move_to(layer.get_center()),
                layer.animate.set_opacity(1),
                run_time=1.0,
            )
            self.play(FadeOut(layer_copy), run_time=0.2)
            self.wait(0.3)

        # Fast forward through remaining offloaded layers
        fast_status = Text(
            t("fast_forward"),
            font_size=18,
            color=GRAY,
        )
        fast_status.to_edge(DOWN, buff=0.1)
        self.play(Transform(phase1_title, fast_status))

        # Quick animation for layers 3-7
        for layer_idx in range(3, 8):
            layer = all_layers[layer_idx]

            # Create temp layer in exchange slot
            temp_layer = layer.copy()
            temp_layer[0].set_fill(ORANGE, opacity=0.8)
            temp_layer.move_to(exchange_slot_pos)

            self.play(
                layer.animate.set_opacity(0.3),
                FadeIn(temp_layer),
                run_time=0.08,
            )
            self.play(
                temp_layer[0].animate.set_fill(YELLOW, opacity=1),
                run_time=0.05,
            )
            self.play(
                FadeOut(temp_layer),
                layer.animate.set_opacity(1),
                run_time=0.08,
            )

        self.wait(0.5)

        # Phase 2: Process GPU-resident layers (8-27)
        phase2_title = Text(
            t("phase2"),
            font_size=22,
            color=GREEN_C,
        )
        phase2_title.to_edge(DOWN, buff=0.1)
        self.play(Transform(phase1_title, phase2_title))
        self.wait(0.3)

        fast_gpu_status = Text(
            t("gpu_direct"),
            font_size=18,
            color=GREEN,
        )
        fast_gpu_status.to_edge(DOWN, buff=0.1)
        self.play(Transform(phase1_title, fast_gpu_status))

        # Quick animation for GPU layers
        for layer_idx in range(8, 28):
            layer = all_layers[layer_idx]
            self.play(
                layer[0].animate.set_fill(YELLOW, opacity=0.9),
                run_time=0.03,
            )
            self.play(
                layer[0].animate.set_fill(GREEN, opacity=0.7),
                run_time=0.02,
            )

        self.wait(0.5)

        # Token generated
        complete_status = Text(
            t("token_generated"),
            font_size=22,
            color=YELLOW,
        )
        complete_status.to_edge(DOWN, buff=0.1)
        self.play(Transform(phase1_title, complete_status))
        self.wait(1)

        self.play(FadeOut(phase1_title))

    def show_summary(self):
        """Show final summary"""
        # Fade out all existing visual elements
        elements_to_fade = [
            self.title,
            self.gpu_region,
            self.cpu_region,
            self.pcie_arrow,
            self.pcie_label,
            self.exchange_slot,
            self.slot_label,
            self.legend,
            *self.all_layers,
        ]
        self.play(
            *[FadeOut(elem) for elem in elements_to_fade],
            run_time=0.8,
        )

        # Show summary
        summary_title = Text(t("summary_title"), font_size=28)
        summary_title.to_edge(UP, buff=0.5)

        # Flow diagram
        header_text = Text(t("for_each_token"), font_size=20, color=YELLOW)

        offload_section = VGroup(
            Text(t("offloaded_layers"), font_size=18, color=BLUE_C),
            Text(t("offload_step1"), font_size=16),
            Text(t("offload_step2"), font_size=16),
            Text(t("offload_step3"), font_size=16),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)

        gpu_section = VGroup(
            Text(t("gpu_layers"), font_size=18, color=GREEN),
            Text(t("gpu_step1"), font_size=16),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)

        flow_items = VGroup(header_text, offload_section, gpu_section)
        flow_items.arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        flow_items.move_to(ORIGIN + UP * 0.5)

        self.play(
            Write(summary_title),
            FadeIn(flow_items),
            run_time=1.5,
        )
        self.wait(2)

        # Benefits
        benefits = VGroup(
            Text(t("benefits"), font_size=20, color=YELLOW),
            Text(t("benefit1"), font_size=16, color=GREEN),
            Text(t("benefit2"), font_size=16, color=GREEN),
            Text(t("benefit3"), font_size=16, color=ORANGE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        benefits.next_to(flow_items, DOWN, buff=0.5)

        self.play(FadeIn(benefits))
        self.wait(3)


class SimpleLayerFlow(Scene):
    """
    Simplified animation focusing purely on the layer flow during one token.
    """

    def construct(self):
        # Title
        title = Text(t("simple_title"), font_size=32)
        title.to_edge(UP, buff=0.4)
        self.play(Write(title))

        # Create simplified view
        # GPU area (right)
        gpu_area = Rectangle(
            width=5, height=4,
            fill_color=ORANGE, fill_opacity=0.1,
            stroke_color=ORANGE, stroke_width=2,
        )
        gpu_area.shift(RIGHT * 2.5 + DOWN * 0.3)
        gpu_label = Text(t("gpu"), font_size=28, color=ORANGE)
        gpu_label.next_to(gpu_area, UP)

        # CPU area (left)
        cpu_area = Rectangle(
            width=3, height=4,
            fill_color=BLUE, fill_opacity=0.1,
            stroke_color=BLUE, stroke_width=2,
        )
        cpu_area.shift(LEFT * 4 + DOWN * 0.3)
        cpu_label = Text(t("cpu"), font_size=28, color=BLUE)
        cpu_label.next_to(cpu_area, UP)

        self.play(
            Create(gpu_area), Create(cpu_area),
            Write(gpu_label), Write(cpu_label),
        )

        # Create exchange slot on GPU (dashed border)
        exchange_slot = RoundedRectangle(
            corner_radius=0.05,
            width=2.2,
            height=0.45,
            stroke_color=YELLOW,
            stroke_width=2,
            fill_opacity=0.1,
            fill_color=YELLOW,
        )
        dashed_slot = DashedVMobject(exchange_slot, num_dashes=15)
        dashed_slot.move_to(gpu_area.get_top() + DOWN * 0.4)
        slot_label = Text(t("exchange_slot"), font_size=11, color=YELLOW)
        slot_label.next_to(dashed_slot, UP, buff=0.05)

        exchange_slot_pos = dashed_slot.get_center()

        self.play(Create(dashed_slot), Write(slot_label))

        # Create layer representations
        # Offloaded layers on CPU
        cpu_layers = VGroup()
        for i in range(4):  # Simplified to 4 offloaded layers
            layer = VGroup(
                RoundedRectangle(
                    width=2, height=0.4,
                    fill_color=BLUE_C, fill_opacity=0.7,
                    stroke_color=BLUE_C,
                    corner_radius=0.05,
                ),
                Text(f"L{i}", font_size=14, color=WHITE),
            )
            layer[1].move_to(layer[0].get_center())
            cpu_layers.add(layer)

        cpu_layers.arrange(DOWN, buff=0.1)
        cpu_layers.move_to(cpu_area.get_center())

        # GPU-resident layers (arranged in 2 columns)
        gpu_layers = VGroup()
        for i in range(6):  # Simplified to 6 GPU layers
            layer = VGroup(
                RoundedRectangle(
                    width=1.8, height=0.35,
                    fill_color=GREEN, fill_opacity=0.7,
                    stroke_color=GREEN,
                    corner_radius=0.05,
                ),
                Text(f"L{i+4}", font_size=12, color=WHITE),
            )
            layer[1].move_to(layer[0].get_center())
            gpu_layers.add(layer)

        # Arrange in 2 columns
        left_col = VGroup(*gpu_layers[0:3])
        right_col = VGroup(*gpu_layers[3:6])
        left_col.arrange(DOWN, buff=0.08)
        right_col.arrange(DOWN, buff=0.08)
        gpu_group = VGroup(left_col, right_col)
        gpu_group.arrange(RIGHT, buff=0.1)
        gpu_group.move_to(gpu_area.get_center() + DOWN * 0.3)

        self.play(FadeIn(cpu_layers), FadeIn(gpu_group))
        self.wait(0.5)

        # Status area
        status = Text(t("ready"), font_size=20, color=YELLOW)
        status.to_edge(DOWN, buff=0.3)
        self.play(Write(status))

        # Animate processing of each offloaded layer
        for i in range(4):
            layer = cpu_layers[i]

            # Step 1: Load to exchange slot
            new_status = Text(t("loading_layer", idx=i), font_size=20, color=BLUE)
            new_status.to_edge(DOWN, buff=0.3)
            self.play(Transform(status, new_status), run_time=0.2)

            # Create a copy that moves to exchange slot
            moving_layer = layer.copy()
            moving_layer[0].set_fill(ORANGE, opacity=0.8)
            moving_layer[0].set_stroke(ORANGE)

            self.play(
                layer.animate.set_opacity(0.3),
                moving_layer.animate.move_to(exchange_slot_pos),
                run_time=0.4,
            )

            # Step 2: Compute
            new_status = Text(t("computing_layer", idx=i), font_size=20, color=ORANGE)
            new_status.to_edge(DOWN, buff=0.3)
            self.play(Transform(status, new_status), run_time=0.15)

            self.play(
                moving_layer[0].animate.set_fill(YELLOW, opacity=1),
                run_time=0.1,
            )
            self.play(
                moving_layer[0].animate.set_fill(ORANGE, opacity=0.8),
                run_time=0.1,
            )

            # Step 3: Offload back
            new_status = Text(t("offloading_layer", idx=i), font_size=20, color=BLUE_C)
            new_status.to_edge(DOWN, buff=0.3)
            self.play(Transform(status, new_status), run_time=0.15)

            self.play(
                moving_layer.animate.move_to(layer.get_center()),
                layer.animate.set_opacity(1),
                run_time=0.3,
            )
            self.remove(moving_layer)

        # Process GPU layers (fast)
        new_status = Text(t("processing_gpu"), font_size=20, color=GREEN)
        new_status.to_edge(DOWN, buff=0.3)
        self.play(Transform(status, new_status))

        for layer in gpu_layers:
            self.play(
                layer[0].animate.set_fill(YELLOW, opacity=1),
                run_time=0.05,
            )
            self.play(
                layer[0].animate.set_fill(GREEN, opacity=0.7),
                run_time=0.03,
            )

        # Complete
        final_status = Text(t("token_done"), font_size=24, color=YELLOW)
        final_status.to_edge(DOWN, buff=0.3)
        self.play(Transform(status, final_status))
        self.wait(2)


class InferenceTimeline(Scene):
    """
    Timeline view showing the sequential processing of layers during inference.
    """

    def construct(self):
        title = Text(t("timeline_title"), font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Create timeline
        timeline_base = Rectangle(
            width=12, height=0.1,
            fill_color=WHITE, fill_opacity=0.3,
        )
        timeline_base.shift(DOWN * 0.5)

        # Layer blocks on timeline
        # Offloaded layers (with transfer overhead)
        offload_blocks = VGroup()

        x_pos = -5.5
        for _ in range(8):
            # Each offloaded layer has: load + compute + offload
            block = VGroup()

            # Load phase
            load = Rectangle(
                width=0.3, height=0.6,
                fill_color=BLUE, fill_opacity=0.7,
            )
            load.move_to([x_pos, 0, 0])

            # Compute phase
            compute = Rectangle(
                width=0.2, height=0.6,
                fill_color=ORANGE, fill_opacity=0.9,
            )
            compute.next_to(load, RIGHT, buff=0)

            # Offload phase
            offload = Rectangle(
                width=0.3, height=0.6,
                fill_color=BLUE_C, fill_opacity=0.7,
            )
            offload.next_to(compute, RIGHT, buff=0)

            block.add(load, compute, offload)
            offload_blocks.add(block)

            x_pos += 0.85

        # GPU-resident layers (compute only)
        gpu_blocks = VGroup()
        for _ in range(20):
            block = Rectangle(
                width=0.15, height=0.6,
                fill_color=GREEN, fill_opacity=0.8,
            )
            block.move_to([x_pos, 0, 0])
            gpu_blocks.add(block)
            x_pos += 0.17

        # Labels
        offload_label = Text(t("offloaded_layers_label"), font_size=14, color=BLUE_C)
        offload_label.next_to(offload_blocks, UP, buff=0.2)

        gpu_label = Text(t("gpu_layers_label"), font_size=14, color=GREEN)
        gpu_label.next_to(gpu_blocks, UP, buff=0.2)

        # Legend
        legend = VGroup(
            VGroup(
                Rectangle(width=0.3, height=0.2, fill_color=BLUE, fill_opacity=0.7, stroke_width=0),
                Text(t("cpu_to_gpu"), font_size=12),
            ).arrange(RIGHT, buff=0.1),
            VGroup(
                Rectangle(width=0.3, height=0.2, fill_color=ORANGE, fill_opacity=0.9, stroke_width=0),
                Text(t("compute"), font_size=12),
            ).arrange(RIGHT, buff=0.1),
            VGroup(
                Rectangle(width=0.3, height=0.2, fill_color=BLUE_C, fill_opacity=0.7, stroke_width=0),
                Text(t("gpu_to_cpu"), font_size=12),
            ).arrange(RIGHT, buff=0.1),
            VGroup(
                Rectangle(width=0.3, height=0.2, fill_color=GREEN, fill_opacity=0.8, stroke_width=0),
                Text(t("gpu_direct_label"), font_size=12),
            ).arrange(RIGHT, buff=0.1),
        ).arrange(RIGHT, buff=0.5)
        legend.to_edge(DOWN, buff=0.5)

        # Time arrow
        time_arrow = Arrow(LEFT * 6, RIGHT * 6, color=WHITE, stroke_width=2)
        time_arrow.shift(DOWN * 1.5)
        time_label = Text(t("time"), font_size=16)
        time_label.next_to(time_arrow, RIGHT)

        # Animate
        self.play(Create(timeline_base))
        self.play(
            FadeIn(offload_blocks),
            Write(offload_label),
        )
        self.play(
            FadeIn(gpu_blocks),
            Write(gpu_label),
        )
        self.play(
            FadeIn(legend),
            Create(time_arrow),
            Write(time_label),
        )

        # Highlight the overhead
        overhead_text = Text(
            t("overhead"),
            font_size=16,
            color=YELLOW,
        )
        overhead_text.shift(DOWN * 2.5)
        self.play(Write(overhead_text))

        fast_text = Text(
            t("fast"),
            font_size=16,
            color=GREEN,
        )
        fast_text.shift(DOWN * 3)
        self.play(Write(fast_text))

        self.wait(3)


if __name__ == "__main__":
    print("VRAM Layer Offloading Animation")
    print("=" * 40)
    print("\nAvailable scenes:")
    print("  - LayerOffloadingDemo    : Main comprehensive demo")
    print("  - SimpleLayerFlow        : Simplified flow animation")
    print("  - InferenceTimeline      : Timeline view of layer processing")
    print("\nUsage (English - default):")
    print("  manim -pql vram_offload_animation.py LayerOffloadingDemo")
    print("  manim -pqh vram_offload_animation.py LayerOffloadingDemo  # High quality")
    print("\nUsage (Chinese / 中文):")
    print("  LANG=zh manim -pql vram_offload_animation.py LayerOffloadingDemo")
    print("  LANG=zh manim -pqh vram_offload_animation.py LayerOffloadingDemo  # 高质量")
    print(f"\nCurrent language: {LANGUAGE}")
