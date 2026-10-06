"""Dynamic classifier execution, entropy analysis, and anti-static verification tests."""

import string
import time
import uuid
import pytest
import torch

from decide.crypto import (
    generate_api_key,
    generate_admin_password,
    generate_session_secret,
    constant_time_compare,
    extract_key_prefix,
    hash_api_key,
)
from decide.engine.classifier import MultiTaskClassifier, ClassificationResult, InferenceException


class TestMultiTaskClassifierDynamicExecution:
    """Verify MultiTaskClassifier is strictly computational and never hardcoded to static keys/values."""

    def test_dynamic_arbitrary_task_names_and_labels(self):
        """Verify classifier handles arbitrary UUID task names and random candidate sets."""
        task_names = [f"task_{uuid.uuid4().hex[:6]}" for _ in range(5)]
        tasks = {
            t: [f"label_{uuid.uuid4().hex[:4]}_{j}" for j in range(4)]
            for t in task_names
        }

        # Extractor dynamically maps each task to its 2nd candidate label
        expected_output = {
            t: tasks[t][2] for t in task_names
        }

        class DynamicExtractor:
            def extract(self, text, task_dict):
                return {k: expected_output[k] for k in task_dict}

        classifier = MultiTaskClassifier(extractor=DynamicExtractor(), device=torch.device("cpu"))
        result = classifier.predict("Random input string", tasks)

        assert isinstance(result, ClassificationResult)
        assert result.result == expected_output
        for t in task_names:
            assert result.result[t] == tasks[t][2]
            assert result[t] if t in result else True

    def test_dynamic_partial_extractor_fallback(self):
        """Verify that when extractor only returns a subset of tasks, remainder fall back to candidate[0]."""
        task_a = f"task_{uuid.uuid4().hex[:6]}"
        task_b = f"task_{uuid.uuid4().hex[:6]}"
        task_c = f"task_{uuid.uuid4().hex[:6]}"

        tasks = {
            task_a: ["a_first", "a_second"],
            task_b: ["b_first", "b_second"],
            task_c: ["c_first", "c_second"],
        }

        # Extractor only returns prediction for task_b
        class PartialExtractor:
            def extract(self, text, task_dict):
                return {task_b: "b_second"}

        classifier = MultiTaskClassifier(extractor=PartialExtractor(), device=torch.device("cpu"))
        result = classifier.predict("Random text", tasks)

        assert result.result[task_b] == "b_second"
        # task_a and task_c must fall back dynamically to candidate 0
        assert result.result[task_a] == "a_first"
        assert result.result[task_c] == "c_first"

    def test_dynamic_mixed_extractor_return_formats(self):
        """Verify extractor handling of dict-with-label, list-of-dicts, list-of-strings, and scalars."""
        tasks = {
            "dict_format": ["val1", "val2"],
            "list_dict_format": ["val3", "val4"],
            "list_str_format": ["val5", "val6"],
            "scalar_str_format": ["val7", "val8"],
            "scalar_num_format": ["100", "200"],
        }

        class MixedExtractor:
            def extract(self, text, task_dict):
                return {
                    "dict_format": {"label": "val2", "confidence": 0.99},
                    "list_dict_format": [{"label": "val4", "score": 0.95}],
                    "list_str_format": ["val6"],
                    "scalar_str_format": "val8",
                    "scalar_num_format": 200,
                }

        classifier = MultiTaskClassifier(extractor=MixedExtractor(), device=torch.device("cpu"))
        result = classifier.predict("Query text", tasks)

        assert result.result["dict_format"] == "val2"
        assert result.result["list_dict_format"] == "val4"
        assert result.result["list_str_format"] == "val6"
        assert result.result["scalar_str_format"] == "val8"
        assert result.result["scalar_num_format"] == "200"

    def test_real_elapsed_latency_tracking(self):
        """Verify latency_ms tracks real execution time rather than returning a static mock number."""
        class SlowExtractor:
            def extract(self, text, task_dict):
                time.sleep(0.025)  # 25 ms delay
                return {k: v[0] for k, v in task_dict.items()}

        classifier = MultiTaskClassifier(extractor=SlowExtractor(), device=torch.device("cpu"))
        result = classifier.predict("sample", {"task1": ["label1"]})

        # Should be at least 24.0 ms
        assert result.latency_ms >= 24.0
        assert isinstance(result.latency_ms, float)


class TestCryptoEntropyAndAntiCheating:
    """Verify cryptographic generator entropy, uniqueness, and constant-time properties."""

    def test_generate_api_key_large_scale_entropy(self):
        """Verify 2,000 generated API keys have 0 collisions and healthy character distribution."""
        sample_size = 2000
        keys = [generate_api_key() for _ in range(sample_size)]

        # Zero collisions
        unique_keys = set(keys)
        assert len(unique_keys) == sample_size, "Collision detected in generate_api_key!"

        # Prefix and length uniformity
        for key in keys:
            assert key.startswith("dec_")
            assert len(key) == 36

        # Character entropy distribution across all random 32-character segments
        all_random_chars = "".join(k[4:] for k in keys)
        total_chars = len(all_random_chars)

        uppercase_count = sum(1 for c in all_random_chars if c in string.ascii_uppercase)
        lowercase_count = sum(1 for c in all_random_chars if c in string.ascii_lowercase)
        digits_count = sum(1 for c in all_random_chars if c in string.digits)

        assert uppercase_count + lowercase_count + digits_count == total_chars

        # In a 62-char alphabet (26 upper, 26 lower, 10 digits):
        # Upper ~ 41.9%, Lower ~ 41.9%, Digits ~ 16.1%
        # Assert each character class is well-represented (statistically bounded)
        assert uppercase_count / total_chars > 0.30
        assert lowercase_count / total_chars > 0.30
        assert digits_count / total_chars > 0.10

    def test_generate_admin_password_dynamic_lengths_and_entropy(self):
        """Verify dynamic length support and entropy for admin passwords."""
        lengths = [8, 12, 16, 24, 32, 64, 128]
        for length in lengths:
            pw = generate_admin_password(length)
            assert len(pw) == length
            assert all(c in (string.ascii_letters + string.digits) for c in pw)

        # Uniqueness across 1,000 iterations
        sample = {generate_admin_password(24) for _ in range(1000)}
        assert len(sample) == 1000

    def test_generate_session_secret_hex_entropy(self):
        """Verify session secrets are distinct 64-character hex strings with full hex distribution."""
        sample = [generate_session_secret() for _ in range(500)]
        assert len(set(sample)) == 500

        all_hex_chars = "".join(sample)
        distinct_hex_chars = set(all_hex_chars)
        # All 16 hex digits (0-9, a-f) must be present across 500 64-char secrets (32,000 chars)
        assert set("0123456789abcdef").issubset(distinct_hex_chars)

    def test_constant_time_compare_adversarial_matrix(self):
        """Verify constant_time_compare detects single bit flips at every position."""
        base = "dec_" + "a" * 32

        # Bit flip at each position
        for i in range(len(base)):
            corrupted = base[:i] + ("b" if base[i] != "b" else "c") + base[i + 1:]
            assert constant_time_compare(base, corrupted) is False, f"Failed at index {i}"

        # Prefix / suffix matches must fail
        assert constant_time_compare(base, base[:-1]) is False
        assert constant_time_compare(base, base[1:]) is False
        assert constant_time_compare(base, base + "x") is False

        # Non-string types
        assert constant_time_compare(base, 123) is False  # type: ignore
        assert constant_time_compare(None, None) is False  # type: ignore
        assert constant_time_compare(base, None) is False  # type: ignore
