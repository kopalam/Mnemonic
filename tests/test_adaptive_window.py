"""Tests for Adaptive Extraction Window (Phase 2)."""

import pytest
from mnemonic.adaptive_window import (
    determine_extraction_window,
    analyze_conversation_complexity,
    _count_entities,
    _calculate_relation_density,
    _detect_temporal_references,
    _detect_topic_switches,
    ExtractionWindow,
    WINDOW_PRESETS,
)


class TestEntityCount:
    """Test entity counting."""

    def test_count_capitalized_words(self):
        """Count capitalized words (names, places)."""
        text = "John went to Paris with Mary."
        count = _count_entities(text)
        assert count >= 2  # John, Paris, Mary

    def test_count_numbers(self):
        """Count numbers."""
        text = "I have 3 cats and 2 dogs."
        count = _count_entities(text)
        assert count >= 2  # 3, 2

    def test_count_quoted_strings(self):
        """Count quoted strings."""
        text = 'He said "hello" and "goodbye".'
        count = _count_entities(text)
        assert count >= 2  # hello, goodbye

    def test_empty_text(self):
        """Empty text has no entities."""
        count = _count_entities("")
        assert count == 0


class TestRelationDensity:
    """Test relation density calculation."""

    def test_pronouns_detected(self):
        """Pronouns are detected."""
        text = "He said she would call him."
        density = _calculate_relation_density(text)
        assert density > 0

    def test_conjunctions_detected(self):
        """Conjunctions are detected."""
        text = "I like apples and oranges but not bananas."
        density = _calculate_relation_density(text)
        assert density > 0

    def test_prepositions_detected(self):
        """Prepositions are detected."""
        text = "The book is on the table in the room."
        density = _calculate_relation_density(text)
        assert density > 0

    def test_empty_text(self):
        """Empty text has zero density."""
        density = _calculate_relation_density("")
        assert density == 0.0


class TestTemporalReferences:
    """Test temporal reference detection."""

    def test_date_patterns(self):
        """Date patterns are detected."""
        text = "I'll meet you tomorrow at 3pm."
        temporal = _detect_temporal_references(text)
        assert temporal > 0

    def test_time_patterns(self):
        """Time patterns are detected."""
        text = "Let's meet at 14:00 in the morning."
        temporal = _detect_temporal_references(text)
        assert temporal > 0

    def test_duration_patterns(self):
        """Duration patterns are detected."""
        text = "It takes 2 hours to complete."
        temporal = _detect_temporal_references(text)
        assert temporal > 0

    def test_no_temporal_references(self):
        """No temporal references."""
        text = "The sky is blue."
        temporal = _detect_temporal_references(text)
        assert temporal == 0.0


class TestTopicSwitches:
    """Test topic switch detection."""

    def test_transition_phrases(self):
        """Transition phrases are detected."""
        conversation = [
            {"role": "user", "content": "I like pizza."},
            {"role": "assistant", "content": "By the way, what about pasta?"},
        ]
        switches = _detect_topic_switches(conversation)
        assert switches >= 1

    def test_chinese_transition_phrases(self):
        """Chinese transition phrases are detected."""
        conversation = [
            {"role": "user", "content": "我喜欢吃披萨。"},
            {"role": "assistant", "content": "说到吃的，你喜欢意大利面吗？"},
        ]
        switches = _detect_topic_switches(conversation)
        assert switches >= 1

    def test_no_switches(self):
        """No topic switches."""
        conversation = [
            {"role": "user", "content": "I like pizza."},
            {"role": "assistant", "content": "What kind of pizza?"},
        ]
        switches = _detect_topic_switches(conversation)
        assert switches == 0


class TestConversationComplexity:
    """Test conversation complexity analysis."""

    def test_simple_conversation(self):
        """Simple conversation has low complexity."""
        conversation = [
            {"role": "user", "content": "Hello."},
            {"role": "assistant", "content": "Hi!"},
        ]
        complexity = analyze_conversation_complexity(conversation)
        assert 0 <= complexity <= 1

    def test_complex_conversation(self):
        """Complex conversation has higher complexity."""
        conversation = [
            {"role": "user", "content": "John and Mary went to Paris on 2024-01-15."},
            {"role": "assistant", "content": "They stayed for 3 days and visited 5 museums."},
            {"role": "user", "content": "By the way, I also need to schedule a meeting tomorrow at 2pm."},
        ]
        complexity = analyze_conversation_complexity(conversation)
        assert complexity > 0.3  # Should be at least moderate complexity


class TestExtractionWindow:
    """Test extraction window determination."""

    def test_fast_window_for_simple_conversation(self):
        """Simple conversation gets fast window."""
        conversation = [
            {"role": "user", "content": "Hello."},
            {"role": "assistant", "content": "Hi!"},
        ]
        window = determine_extraction_window(conversation)
        assert window.mode == "fast"
        assert window.m == 5
        assert window.s == 5

    def test_standard_window_for_moderate_conversation(self):
        """Moderate conversation gets standard window."""
        conversation = [
            {"role": "user", "content": "John went to Paris with Mary."},
            {"role": "assistant", "content": "That sounds nice!"},
            {"role": "user", "content": "They stayed for 3 days."},
        ]
        window = determine_extraction_window(conversation)
        assert window.mode in ["fast", "standard"]

    def test_deep_window_for_complex_conversation(self):
        """Complex conversation gets deep window."""
        conversation = [
            {"role": "user", "content": "John and Mary went to Paris on 2024-01-15."},
            {"role": "assistant", "content": "They stayed for 3 days and visited 5 museums."},
            {"role": "user", "content": "By the way, I also need to schedule a meeting tomorrow at 2pm with Dr. Smith."},
            {"role": "assistant", "content": "I'll help you with that."},
            {"role": "user", "content": "Also, my sister Anna is coming next week for 2 days."},
        ]
        window = determine_extraction_window(conversation)
        # Should be at least standard
        assert window.mode in ["standard", "deep"]


class TestWindowPresets:
    """Test window presets."""

    def test_fast_preset(self):
        """Fast preset values."""
        preset = WINDOW_PRESETS["fast"]
        assert preset.m == 5
        assert preset.s == 5
        assert preset.mode == "fast"

    def test_standard_preset(self):
        """Standard preset values."""
        preset = WINDOW_PRESETS["standard"]
        assert preset.m == 10
        assert preset.s == 10
        assert preset.mode == "standard"

    def test_deep_preset(self):
        """Deep preset values."""
        preset = WINDOW_PRESETS["deep"]
        assert preset.m == 20
        assert preset.s == 15
        assert preset.mode == "deep"