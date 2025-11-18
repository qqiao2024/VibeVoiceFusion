import pytest
import re
from vibevoice.lora.lora_network import LoRANetwork


class TestLoRANetwork:
    """Test cases for LoRANetwork class"""

    def test_includes_layers(self):
        """Test that _includes_layers returns correct regex patterns for LoRA target layers"""
        # Create a minimal LoRANetwork instance to access _includes_layers
        # We don't need a full model for this test, just the method
        class MinimalLoRANetwork(LoRANetwork):
            def __init__(self):
                # Skip parent __init__ to avoid needing a full model
                pass

        network = MinimalLoRANetwork()
        patterns = network._includes_layers()

        # Verify we get the expected number of patterns
        assert len(patterns) == 5, f"Expected 5 patterns, got {len(patterns)}"

        # Verify all elements are compiled regex patterns
        for pattern in patterns:
            assert isinstance(pattern, re.Pattern), f"Expected re.Pattern, got {type(pattern)}"

        # Test cases for language model self-attention layers
        language_model_attn_cases = [
            "model.language_model.layers.0.self_attn.q_proj",
            "model.language_model.layers.15.self_attn.k_proj",
            "model.language_model.layers.27.self_attn.v_proj",
            "model.language_model.layers.31.self_attn.o_proj",
        ]

        # Test cases for language model MLP layers
        language_model_mlp_cases = [
            "model.language_model.layers.0.mlp.gate_proj",
            "model.language_model.layers.10.mlp.up_proj",
            "model.language_model.layers.20.mlp.down_proj",
        ]
        
        # Test cases for prediction head layers
        prediction_head_cases = [
            "model.prediction_head.cond_proj",
            "model.prediction_head.layers.0.ffn.gate_proj",
            "model.prediction_head.layers.5.ffn.up_proj",
            "model.prediction_head.layers.10.ffn.down_proj",
            "model.prediction_head.layers.0.adaLN_modulation.1",
            "model.prediction_head.layers.7.adaLN_modulation.1",
        ]
        
        # Test cases that should NOT match
        negative_cases = [
            "model.language_model.layers.0.self_attn.bias",
            "model.language_model.layers.0.ln1",
            "model.language_model.embed_tokens",
            "model.prediction_head.layers.0.adaLN_modulation.0",
            "model.prediction_head.layers.0.adaLN_modulation.2",
            "some_other_layer.weight",
        ]
        
        # Combine all positive test cases
        all_positive_cases = language_model_attn_cases + language_model_mlp_cases + prediction_head_cases
        
        # Test that all positive cases match at least one pattern
        for test_case in all_positive_cases:
            matched = any(pattern.search(test_case) for pattern in patterns)
            assert matched, f"Expected '{test_case}' to match at least one pattern"
        
        # Test that negative cases don't match any pattern
        for test_case in negative_cases:
            matched = any(pattern.search(test_case) for pattern in patterns)
            assert not matched, f"Expected '{test_case}' to NOT match any pattern"
    
    def test_includes_layers_specific_patterns(self):
        """Test each specific pattern individually"""
        class MinimalLoRANetwork(LoRANetwork):
            def __init__(self):
                pass
        
        network = MinimalLoRANetwork()
        patterns = network._includes_layers()
        
        # Pattern 0: Language model attention layers
        attn_pattern = patterns[0]
        assert attn_pattern.match("model.language_model.layers.0.self_attn.q_proj"), "should match q_proj"
        assert attn_pattern.match("model.language_model.layers.99.self_attn.k_proj"), "should match k_proj"
        assert not attn_pattern.match("model.language_model.layers.0.self_attn.bias"), "should not match bias"
        
        # Pattern 1: Language model MLP layers
        mlp_pattern = patterns[1]
        assert mlp_pattern.match("model.language_model.layers.0.mlp.gate_proj"), "should match gate_proj"
        assert mlp_pattern.match("model.language_model.layers.50.mlp.up_proj"), "should match up_proj"
        assert not mlp_pattern.match("model.language_model.layers.0.mlp.bias"), "should not match bias"
        
        # Pattern 2: Prediction head conditional projection
        cond_proj_pattern = patterns[2]
        assert cond_proj_pattern.match("model.prediction_head.cond_proj"), "should match cond_proj"
        assert not cond_proj_pattern.match("model.prediction_head.cond_proj.weight"), "should not match model.prediction_head.cond_proj.weight"
        assert not cond_proj_pattern.match("some_other.cond_proj"), "should not match some_other.cond_proj"
        
        # Pattern 3: Prediction head FFN layers
        ffn_pattern = patterns[3]
        assert ffn_pattern.match("model.prediction_head.layers.0.ffn.gate_proj"), "should match gate_proj"
        assert ffn_pattern.match("model.prediction_head.layers.100.ffn.down_proj"), "should match down_proj"
        assert not ffn_pattern.match("model.prediction_head.ffn.gate_proj"), "should not match model.prediction_head.ffn.gate_proj"
        
        # Pattern 4: Prediction head adaLN modulation
        adaln_pattern = patterns[4]
        assert adaln_pattern.match("model.prediction_head.layers.0.adaLN_modulation.1"), "should match adaLN_modulation.1"
        assert adaln_pattern.match("model.prediction_head.layers.25.adaLN_modulation.1"), "should match adaLN_modulation.1"
        assert not adaln_pattern.match("model.prediction_head.layers.0.adaLN_modulation.0"), "should not match adaLN_modulation.0"
        assert not adaln_pattern.match("model.prediction_head.layers.0.adaLN_modulation.2"), "should not match adaLN_modulation.2"


if __name__ == "__main__":
    # Run tests
    test_instance = TestLoRANetwork()

    print("Running test_includes_layers...")
    try:
        test_instance.test_includes_layers()
        print("✓ test_includes_layers passed")
    except AssertionError as e:
        print(f"✗ test_includes_layers failed: {e}")

    print("\nRunning test_includes_layers_specific_patterns...")
    try:
        test_instance.test_includes_layers_specific_patterns()
        print("✓ test_includes_layers_specific_patterns passed")
    except AssertionError as e:
        print(f"✗ test_includes_layers_specific_patterns failed: {e}")

    print("\nAll tests completed!")
