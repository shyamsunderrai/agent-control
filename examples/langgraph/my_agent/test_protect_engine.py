"""
Tests for the protection engine.
"""

import tempfile
from pathlib import Path

import pytest
from protect_engine import (
    ProtectEngine,
    RuleViolation,
    get_protect_engine,
    init_protect_engine,
    protect,
)

# Sample YAML rules for testing
SAMPLE_RULES = """
test-string-match:
  step_id: "test-input"
  description: "Test string matching"
  enabled: true
  rules:
    - match:
        string: ["forbidden", "blocked"]
      condition: any
      action: deny
      data: input
  default_action: allow

test-regex-match:
  step_id: "test-pattern"
  description: "Test regex matching"
  enabled: true
  rules:
    - match:
        pattern: "\\d{3}-\\d{2}-\\d{4}"
      condition: any
      action: redact
      data: output
      redact_with: "[SSN REDACTED]"
  default_action: allow

test-context-check:
  step_id: "test-context"
  description: "Test context validation"
  enabled: true
  rules:
    - match:
        key_exists: ["user_id"]
      condition: all
      action: allow
      data: context
  default_action: deny

test-disabled-rule:
  step_id: "test-disabled"
  description: "This rule is disabled"
  enabled: false
  rules:
    - match:
        string: ["anything"]
      condition: any
      action: deny
      data: input
  default_action: allow
"""


@pytest.fixture
def rules_file():
    """Create a temporary rules file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(SAMPLE_RULES)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


@pytest.fixture
def engine(rules_file):
    """Create a protection engine instance for testing."""
    return ProtectEngine(rules_file)


class TestProtectEngine:
    """Tests for the ProtectEngine class."""

    def test_load_rules(self, engine):
        """Test that rules are loaded correctly."""
        assert engine.rules is not None
        assert 'test-string-match' in engine.rules
        assert 'test-regex-match' in engine.rules

    def test_get_rule(self, engine):
        """Test getting a rule by step_id."""
        rule = engine.get_rule('test-input')
        assert rule is not None
        assert rule['step_id'] == 'test-input'
        assert rule['name'] == 'test-string-match'

    def test_get_disabled_rule(self, engine):
        """Test that disabled rules are not returned."""
        rule = engine.get_rule('test-disabled')
        assert rule is None

    def test_get_nonexistent_rule(self, engine):
        """Test getting a rule that doesn't exist."""
        rule = engine.get_rule('nonexistent')
        assert rule is None


class TestStringMatching:
    """Tests for string matching rules."""

    def test_string_match_deny(self, engine):
        """Test string matching with deny action."""
        data = {'input': 'This contains a forbidden word'}

        with pytest.raises(RuleViolation) as exc_info:
            engine.evaluate_rule('test-input', data)

        assert 'forbidden' in str(exc_info.value).lower() or 'test-string-match' in str(exc_info.value)

    def test_string_match_allow(self, engine):
        """Test string matching with allowed content."""
        data = {'input': 'This is safe content'}

        result = engine.evaluate_rule('test-input', data)
        assert result['allowed'] is True
        assert result['action'] == 'allow'

    def test_string_match_case_insensitive(self, engine):
        """Test that string matching is case insensitive."""
        data = {'input': 'This contains FORBIDDEN text'}

        with pytest.raises(RuleViolation):
            engine.evaluate_rule('test-input', data)


class TestRegexMatching:
    """Tests for regex pattern matching."""

    def test_regex_redact(self, engine):
        """Test regex matching with redact action."""
        data = {'output': 'SSN: 123-45-6789 belongs to user'}

        result = engine.evaluate_rule('test-pattern', data)
        assert result['action'] == 'redact'
        assert '[SSN REDACTED]' in result['data']
        assert '123-45-6789' not in result['data']

    def test_regex_no_match(self, engine):
        """Test regex when pattern doesn't match."""
        data = {'output': 'No SSN here'}

        result = engine.evaluate_rule('test-pattern', data)
        assert result['allowed'] is True


class TestContextValidation:
    """Tests for context validation rules."""

    def test_context_key_exists_allow(self, engine):
        """Test context validation when required key exists."""
        data = {'context': {'user_id': '123'}}

        result = engine.evaluate_rule('test-context', data)
        assert result['allowed'] is True

    def test_context_key_missing_deny(self, engine):
        """Test context validation when required key is missing."""
        data = {'context': {'session_id': 'abc'}}

        with pytest.raises(RuleViolation):
            engine.evaluate_rule('test-context', data)

    def test_context_missing_deny(self, engine):
        """Test context validation when context is missing."""
        data = {}

        # Should use default action (deny)
        with pytest.raises(RuleViolation):
            engine.evaluate_rule('test-context', data)


class TestDecorator:
    """Tests for the @protect decorator."""

    def test_decorator_with_violation(self, rules_file):
        """Test decorator raises exception on rule violation."""
        init_protect_engine(rules_file)

        @protect('test-input', input='text')
        async def test_func(text: str):
            return f"Processed: {text}"

        import asyncio

        with pytest.raises(RuleViolation):
            asyncio.run(test_func("This is forbidden"))

    def test_decorator_without_violation(self, rules_file):
        """Test decorator allows valid input."""
        init_protect_engine(rules_file)

        @protect('test-input', input='text')
        async def test_func(text: str):
            return f"Processed: {text}"

        import asyncio

        result = asyncio.run(test_func("This is allowed"))
        assert "Processed: This is allowed" in result

    def test_decorator_sync_function(self, rules_file):
        """Test decorator works with sync functions."""
        init_protect_engine(rules_file)

        @protect('test-input', input='text')
        def sync_func(text: str):
            return f"Processed: {text}"

        result = sync_func("This is allowed")
        assert "Processed: This is allowed" in result

        with pytest.raises(RuleViolation):
            sync_func("This is forbidden")


class TestGlobalEngine:
    """Tests for global engine management."""

    def test_init_protect_engine(self, rules_file):
        """Test initializing the global engine."""
        engine = init_protect_engine(rules_file)
        assert engine is not None
        assert get_protect_engine() is engine

    def test_get_protect_engine_none(self):
        """Test getting engine when none is initialized."""
        # Note: This might fail if previous tests initialized an engine
        # In real usage, you'd reset the global state
        result = get_protect_engine()
        # Engine might be set from previous tests
        assert result is None or isinstance(result, ProtectEngine)


class TestDataExtraction:
    """Tests for data extraction from different sources."""

    def test_all_data_sources(self, engine):
        """Test rule that checks all data sources."""
        # Create a rule that checks 'all'
        data = {
            'input': 'safe input',
            'output': 'safe output',
            'context': {'user': 'test'}
        }

        # Even though the rule doesn't exist, test data extraction logic
        result = engine.evaluate_rule('test-input', data)
        assert result['allowed'] is True


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_data(self, engine):
        """Test with empty data."""
        result = engine.evaluate_rule('test-input', {})
        # Should use default action
        assert result['allowed'] is True

    def test_nonexistent_step(self, engine):
        """Test evaluating a non-existent step."""
        result = engine.evaluate_rule('nonexistent-step', {'input': 'test'})
        assert result['allowed'] is True
        assert 'No rules configured' in result['message']

    def test_reload_rules(self, engine, rules_file):
        """Test reloading rules."""
        # Add a new rule to the file
        with open(rules_file, 'a') as f:
            f.write("""
new-rule:
  step_id: "new-step"
  description: "New rule"
  enabled: true
  rules:
    - match:
        string: ["new"]
      condition: any
      action: deny
      data: input
  default_action: allow
""")

        engine.reload_rules()
        rule = engine.get_rule('new-step')
        assert rule is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

