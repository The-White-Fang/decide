"""Adversarial and boundary test cases to detect static code, shortcuts, and mock-specific stubs."""

import uuid
import pytest
from pydantic import ValidationError

from decide.auth.guardrails import PredictInputSchema
from decide.config import get_settings


class TestPredictInputSchemaAdversarial:
    """Stress tests for PredictInputSchema to ensure boundary checks are dynamic and exact."""

    def test_text_length_exact_boundary(self):
        """Verify strict character boundaries: 8000 valid, 8001 invalid, 1 valid, 0 invalid."""
        tasks = {"sentiment": ["positive", "negative"]}

        # Boundary 8000: must be valid
        payload_8000 = PredictInputSchema(text="x" * 8000, tasks=tasks)
        assert len(payload_8000.text) == 8000

        # Boundary 8001: must raise ValidationError
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="x" * 8001, tasks=tasks)
        assert "text" in str(exc.value)

        # Boundary 8002: must raise ValidationError
        with pytest.raises(ValidationError):
            PredictInputSchema(text="x" * 8002, tasks=tasks)

        # Extreme lengths
        with pytest.raises(ValidationError):
            PredictInputSchema(text="x" * 50000, tasks=tasks)

        # Boundary 1: must be valid
        payload_1 = PredictInputSchema(text="a", tasks=tasks)
        assert len(payload_1.text) == 1

        # Boundary 0 (empty): must raise ValidationError
        with pytest.raises(ValidationError):
            PredictInputSchema(text="", tasks=tasks)

    def test_text_multibyte_and_unicode_boundary(self):
        """Verify multibyte UTF-8 characters (emojis, CJK, Arabic, zero-width) behave properly."""
        tasks = {"category": ["test1", "test2"]}

        # Multibyte string under 8000 characters
        multibyte_text = "🚀🔥🎉" * 1000  # 3000 chars
        payload = PredictInputSchema(text=multibyte_text, tasks=tasks)
        assert len(payload.text) == 3000

        # CJK characters
        cjk_text = "自然语言处理与多任务分类" * 200
        payload_cjk = PredictInputSchema(text=cjk_text, tasks=tasks)
        assert payload_cjk.text == cjk_text

        # Arabic text with right-to-left marks
        arabic_text = "تصنيف متعدد المهام لمعالجة اللغة الطبيعية"
        payload_arabic = PredictInputSchema(text=arabic_text, tasks=tasks)
        assert payload_arabic.text == arabic_text

        # Zero-width spaces and control characters
        zw_text = "invisible\u200b\u200c\u200dcharacters\t\n"
        payload_zw = PredictInputSchema(text=zw_text, tasks=tasks)
        assert payload_zw.text == zw_text

        # CJK string exceeding 8000 characters
        with pytest.raises(ValidationError):
            PredictInputSchema(text="中" * 8001, tasks=tasks)

    def test_task_count_exact_boundary(self):
        """Verify task count limit (settings.max_task_count = 20) is strictly enforced."""
        settings = get_settings()
        max_tasks = settings.max_task_count  # 20

        # Exactly 1 task: valid
        payload_1 = PredictInputSchema(text="hello", tasks={"task_1": ["label_a"]})
        assert len(payload_1.tasks) == 1

        # Exactly max_tasks (20): valid
        tasks_20 = {f"dynamic_task_{i}": [f"label_{i}"] for i in range(max_tasks)}
        payload_20 = PredictInputSchema(text="hello", tasks=tasks_20)
        assert len(payload_20.tasks) == max_tasks

        # Exactly max_tasks + 1 (21): invalid
        tasks_21 = {f"dynamic_task_{i}": [f"label_{i}"] for i in range(max_tasks + 1)}
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="hello", tasks=tasks_21)
        assert "exceeds maximum allowed" in str(exc.value)

        # Far above limit (50 tasks)
        tasks_50 = {f"task_{i}": ["label"] for i in range(50)}
        with pytest.raises(ValidationError):
            PredictInputSchema(text="hello", tasks=tasks_50)

    def test_labels_per_task_exact_boundary(self):
        """Verify labels per task limit (settings.max_labels_per_task = 50) is strictly enforced."""
        settings = get_settings()
        max_labels = settings.max_labels_per_task  # 50

        # Exactly 1 label: valid
        payload_1 = PredictInputSchema(text="hello", tasks={"t": ["single_label"]})
        assert len(payload_1.tasks["t"]) == 1

        # Exactly max_labels (50 distinct labels): valid
        labels_50 = [f"label_{uuid.uuid4().hex[:8]}_{i}" for i in range(max_labels)]
        payload_50 = PredictInputSchema(text="hello", tasks={"t": labels_50})
        assert len(payload_50.tasks["t"]) == max_labels

        # Exactly max_labels + 1 (51 distinct labels): invalid
        labels_51 = [f"label_{uuid.uuid4().hex[:8]}_{i}" for i in range(max_labels + 1)]
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="hello", tasks={"t": labels_51})
        assert "exceeding maximum of" in str(exc.value)

    def test_task_name_and_label_length_boundaries(self):
        """Verify 100 character limits on task names and label strings."""
        # Task name: exactly 100 characters (valid)
        t_100 = "t" * 100
        payload_t100 = PredictInputSchema(text="hello", tasks={t_100: ["valid_label"]})
        assert t_100 in payload_t100.tasks

        # Task name: 101 characters (invalid)
        t_101 = "t" * 101
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="hello", tasks={t_101: ["valid_label"]})
        assert "exceeds 100 characters" in str(exc.value)

        # Label: exactly 100 characters (valid)
        l_100 = "l" * 100
        payload_l100 = PredictInputSchema(text="hello", tasks={"t": [l_100]})
        assert payload_l100.tasks["t"][0] == l_100

        # Label: 101 characters (invalid)
        l_101 = "l" * 101
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="hello", tasks={"t": [l_101]})
        assert "exceeds maximum length of 100 characters" in str(exc.value)

    def test_duplicate_labels_with_whitespace_and_casing(self):
        """Verify duplicate label detection handles trailing/leading whitespace and variations."""
        # Exact duplicate
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="sample", tasks={"t": ["apple", "apple"]})
        assert "Duplicate label" in str(exc.value)

        # Duplicate with whitespace padding
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="sample", tasks={"t": ["banana", "  banana  "]})
        assert "Duplicate label" in str(exc.value)

        # Duplicate with tab/newline padding
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="sample", tasks={"t": ["cherry", "\tcherry\n"]})
        assert "Duplicate label" in str(exc.value)

    def test_malformed_and_empty_task_structures(self):
        """Verify malformed task structures (empty string names, whitespace names, empty lists)."""
        # Empty string task name
        with pytest.raises(ValidationError):
            PredictInputSchema(text="sample", tasks={"": ["label1"]})

        # Whitespace-only task name
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="sample", tasks={"   ": ["label1"]})
        assert "Task names must be non-empty strings" in str(exc.value)

        # Empty label list
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="sample", tasks={"t": []})
        assert "must have at least one candidate label" in str(exc.value)

        # Empty string label
        with pytest.raises(ValidationError):
            PredictInputSchema(text="sample", tasks={"t": [""]})

        # Whitespace-only label
        with pytest.raises(ValidationError) as exc:
            PredictInputSchema(text="sample", tasks={"t": ["   "]})
        assert "must be non-empty strings" in str(exc.value)

    def test_type_tampering_and_non_dict_inputs(self):
        """Verify non-conforming types (int, list, bool) raise validation errors."""
        # Non-string text
        with pytest.raises(ValidationError):
            PredictInputSchema(text=12345, tasks={"t": ["l"]})  # type: ignore

        # List instead of dict for tasks
        with pytest.raises(ValidationError):
            PredictInputSchema(text="sample", tasks=["t1", "t2"])  # type: ignore

        # None as tasks
        with pytest.raises(ValidationError):
            PredictInputSchema(text="sample", tasks=None)  # type: ignore

        # Integer as label in list
        with pytest.raises(ValidationError):
            PredictInputSchema(text="sample", tasks={"t": [123, 456]})  # type: ignore
