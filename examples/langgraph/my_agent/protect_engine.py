"""
Protection engine for YAML-based policy enforcement.

This module provides a decorator-based system for applying fine-grained
controls at different steps in your agent's execution flow.
"""

import asyncio
import inspect
import os
import re
import time
from collections import defaultdict
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import yaml

# Optional: Import agent_protect if available
try:
    import sys

    # Try to import from the unified package
    from agent_protect import AgentProtectClient
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


class RuleViolation(Exception):
    """Raised when a rule violation is detected."""

    def __init__(self, rule_name: str, message: str, action: str = "deny"):
        self.rule_name = rule_name
        self.message = message
        self.action = action
        super().__init__(f"Rule '{rule_name}': {message}")


class ProtectEngine:
    """
    Engine for loading and evaluating YAML-based protection rules.

    Attributes:
        rules: Loaded rules from YAML file or server
        rate_limit_tracker: Track request counts for rate limiting
        agent_id: Optional agent identifier for server registration
        server_url: Optional server URL for fetching rules
    """

    def __init__(
        self,
        rules_file: str | Path | None = None,
        agent_id: str | None = None,
        server_url: str | None = None,
        auto_discover: bool = True
    ):
        """
        Initialize the protection engine.

        Args:
            rules_file: Path to the YAML rules file (optional if using server)
            agent_id: Agent identifier for server registration
            server_url: Server URL for fetching rules dynamically
            auto_discover: Auto-discover rules.yaml in calling context
        """
        self.rules_file = Path(rules_file) if rules_file else None
        self.agent_id = agent_id or self._generate_agent_id()
        self.server_url = server_url or os.getenv('AGENT_PROTECT_URL', 'http://localhost:8000')
        self.rules: dict[str, Any] = {}
        self.rate_limit_tracker: dict[str, list[float]] = defaultdict(list)
        self.registered = False

        # Auto-discover rules.yaml if not specified
        if auto_discover and not self.rules_file:
            self.rules_file = self._auto_discover_rules()

        # Load rules from file or server
        if self.rules_file and self.rules_file.exists():
            self.load_rules()
        else:
            # Try to fetch from server
            self._fetch_rules_from_server()

    def _generate_agent_id(self) -> str:
        """Generate a unique agent ID based on the calling context."""
        # Get the caller's frame to determine agent location
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_file = frame.f_back.f_back.f_code.co_filename
            agent_name = Path(caller_file).stem
            return f"agent-{agent_name}-{os.getpid()}"
        return f"agent-{os.getpid()}"

    def _auto_discover_rules(self) -> Path | None:
        """
        Auto-discover rules.yaml in the calling context.

        Looks for rules.yaml in:
        1. Same directory as the calling file
        2. Current working directory
        3. Parent directory
        """
        # Get caller's directory
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_file = frame.f_back.f_back.f_code.co_filename
            caller_dir = Path(caller_file).parent

            # Try same directory
            rules_path = caller_dir / "rules.yaml"
            if rules_path.exists():
                return rules_path

        # Try current working directory
        cwd_rules = Path.cwd() / "rules.yaml"
        if cwd_rules.exists():
            return cwd_rules

        # Try parent directory
        parent_rules = Path.cwd().parent / "rules.yaml"
        if parent_rules.exists():
            return parent_rules

        return None

    def _fetch_rules_from_server(self) -> None:
        """Fetch rules from the Agent Protect server."""
        if not SDK_AVAILABLE:
            print("⚠️  Agent Protect SDK not available. Using empty rules.")
            self.rules = {}
            return

        try:
            # Synchronous registration for now
            # In production, you might want to do this async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._register_and_fetch())
            loop.close()
        except Exception as e:
            print(f"⚠️  Failed to fetch rules from server: {e}")
            print("   Using empty rules. Agent will run without protection.")
            self.rules = {}

    async def _register_and_fetch(self) -> None:
        """Register agent with server and fetch rules."""
        async with AgentProtectClient(base_url=self.server_url) as client:
            # Register the agent
            # In a real implementation, the server would have an endpoint for this
            print(f"✓ Agent '{self.agent_id}' connecting to {self.server_url}")

            # For now, check server health
            try:
                health = await client.health_check()
                print(f"✓ Server healthy: {health['status']}")
                self.registered = True
            except Exception as e:
                print(f"✗ Server unavailable: {e}")
                raise

            # TODO: In production, fetch rules from server API
            # rules_response = await client.fetch_agent_rules(self.agent_id)
            # self.rules = rules_response['rules']

            print(f"✓ Agent '{self.agent_id}' registered with server")

    def load_rules(self) -> None:
        """Load rules from the YAML file."""
        if not self.rules_file.exists():
            raise FileNotFoundError(f"Rules file not found: {self.rules_file}")

        with open(self.rules_file) as f:
            self.rules = yaml.safe_load(f) or {}

    def reload_rules(self) -> None:
        """Reload rules from the YAML file (for hot-reloading)."""
        self.load_rules()

    def get_rule(self, step_id: str) -> dict[str, Any] | None:
        """
        Get the rule configuration for a given step_id.

        Args:
            step_id: The step identifier

        Returns:
            Rule configuration or None if not found
        """
        for rule_name, rule_config in self.rules.items():
            if rule_config.get('step_id') == step_id and rule_config.get('enabled', True):
                return {**rule_config, 'name': rule_name}
        return None

    def evaluate_rule(
        self,
        step_id: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Evaluate rules for a given step.

        Args:
            step_id: The step identifier
            data: Dictionary containing input, output, context, etc.

        Returns:
            Dictionary with evaluation results

        Raises:
            RuleViolation: If a deny action is triggered
        """
        rule = self.get_rule(step_id)

        if not rule:
            # No rule found for this step_id
            return {
                'allowed': True,
                'action': 'allow',
                'message': 'No rules configured for this step'
            }

        # Extract data based on rule configuration
        data_sources = self._get_data_sources(rule, data)

        # Evaluate each rule
        for rule_spec in rule.get('rules', []):
            result = self._evaluate_single_rule(rule_spec, data_sources, rule['name'])

            if result['action'] == 'deny':
                raise RuleViolation(
                    rule_name=rule['name'],
                    message=result['message'],
                    action='deny'
                )
            elif result['action'] == 'redact':
                # Apply redaction and return modified data
                return {
                    'allowed': True,
                    'action': 'redact',
                    'data': result.get('redacted_data'),
                    'message': result['message']
                }
            elif result['action'] == 'warn':
                # Log warning but allow
                return {
                    'allowed': True,
                    'action': 'warn',
                    'message': result['message']
                }

        # Default action if no rules matched
        default_action = rule.get('default_action', 'allow')

        if default_action == 'deny':
            raise RuleViolation(
                rule_name=rule['name'],
                message='Default action is deny',
                action='deny'
            )

        return {
            'allowed': True,
            'action': 'allow',
            'message': 'All rules passed'
        }

    def _get_data_sources(self, rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract relevant data sources based on rule configuration.

        Args:
            rule: Rule configuration
            data: All available data

        Returns:
            Dictionary of relevant data sources
        """
        data_sources = {}

        # Check what data fields are referenced in the rules
        for rule_spec in rule.get('rules', []):
            data_field = rule_spec.get('data', 'all')

            if data_field == 'all':
                # Include everything
                data_sources.update(data)
            elif data_field in data:
                data_sources[data_field] = data[data_field]

        return data_sources

    def _evaluate_single_rule(
        self,
        rule_spec: dict[str, Any],
        data_sources: dict[str, Any],
        rule_name: str
    ) -> dict[str, Any]:
        """
        Evaluate a single rule specification.

        Args:
            rule_spec: Rule specification
            data_sources: Data to check
            rule_name: Name of the parent rule

        Returns:
            Evaluation result
        """
        data_field = rule_spec.get('data', 'all')
        match_config = rule_spec.get('match', {})
        condition = rule_spec.get('condition', 'any')
        action = rule_spec.get('action', 'allow')

        # Get the data to check
        if data_field == 'all':
            data_to_check = ' '.join(str(v) for v in data_sources.values() if v)
        elif data_field in data_sources:
            data_to_check = data_sources[data_field]
        else:
            # Data field not present, use default action
            return {
                'action': 'allow',
                'message': f'Data field {data_field} not present'
            }

        # Evaluate match conditions
        matches = []

        # String matching
        if 'string' in match_config:
            strings_to_match = match_config['string']
            for s in strings_to_match:
                if isinstance(data_to_check, str):
                    matches.append(s.lower() in data_to_check.lower())
                elif isinstance(data_to_check, (list, dict)):
                    matches.append(s.lower() in str(data_to_check).lower())

        # Pattern (regex) matching
        if 'pattern' in match_config:
            pattern = match_config['pattern']
            if isinstance(data_to_check, str):
                matches.append(bool(re.search(pattern, data_to_check)))
            else:
                matches.append(bool(re.search(pattern, str(data_to_check))))

        # Key existence check
        if 'key_exists' in match_config:
            keys = match_config['key_exists']
            if isinstance(data_to_check, dict):
                for key in keys:
                    matches.append(key in data_to_check)

        # Message count check
        if 'message_count' in match_config:
            count_config = match_config['message_count']
            if isinstance(data_to_check, list):
                count = len(data_to_check)
                if 'max' in count_config:
                    matches.append(count > count_config['max'])
                if 'min' in count_config:
                    matches.append(count < count_config['min'])

        # Rate limiting check
        if 'rate' in match_config:
            rate_config = match_config['rate']
            user_id = data_sources.get('metadata', {}).get('user_id', 'anonymous')
            matches.append(self._check_rate_limit(user_id, rate_config))

        # Custom field check
        if 'custom' in match_config:
            custom = match_config['custom']
            field_value = data_sources.get('context', {}).get(custom['field'])
            operator = custom.get('operator', '==')
            expected = custom['value']

            if operator == '==':
                matches.append(field_value == expected)
            elif operator == '!=':
                matches.append(field_value != expected)
            elif operator == 'in':
                matches.append(field_value in expected)
            elif operator == 'not_in':
                matches.append(field_value not in expected)

        # Evaluate condition
        if condition == 'any':
            rule_matched = any(matches) if matches else False
        elif condition == 'all':
            rule_matched = all(matches) if matches else False
        elif condition == 'none':
            rule_matched = not any(matches) if matches else False
        else:
            rule_matched = False

        if rule_matched:
            message = rule_spec.get('message', f'Rule {rule_name} triggered')

            if action == 'redact':
                # Apply redaction
                redact_with = rule_spec.get('redact_with', '[REDACTED]')
                redacted = self._apply_redaction(
                    data_to_check,
                    match_config,
                    redact_with
                )
                return {
                    'action': 'redact',
                    'message': message,
                    'redacted_data': redacted
                }

            return {
                'action': action,
                'message': message
            }

        return {
            'action': 'allow',
            'message': 'Rule did not match'
        }

    def _check_rate_limit(self, user_id: str, rate_config: dict[str, int]) -> bool:
        """
        Check if rate limit is exceeded.

        Args:
            user_id: User identifier
            rate_config: Rate limit configuration

        Returns:
            True if rate limit exceeded, False otherwise
        """
        window = rate_config.get('window', 60)
        max_requests = rate_config.get('max_requests', 10)

        now = time.time()

        # Clean old entries
        self.rate_limit_tracker[user_id] = [
            ts for ts in self.rate_limit_tracker[user_id]
            if now - ts < window
        ]

        # Check if limit exceeded
        if len(self.rate_limit_tracker[user_id]) >= max_requests:
            return True

        # Add current request
        self.rate_limit_tracker[user_id].append(now)
        return False

    def _apply_redaction(
        self,
        data: Any,
        match_config: dict[str, Any],
        redact_with: str
    ) -> Any:
        """
        Apply redaction to matched patterns.

        Args:
            data: Data to redact
            match_config: Match configuration
            redact_with: Replacement text

        Returns:
            Redacted data
        """
        if not isinstance(data, str):
            return data

        redacted = data

        if 'pattern' in match_config:
            pattern = match_config['pattern']
            redacted = re.sub(pattern, redact_with, redacted)

        if 'string' in match_config:
            for s in match_config['string']:
                redacted = redacted.replace(s, redact_with)

        return redacted


# Global protect engine instance
_protect_engine: ProtectEngine | None = None


def init_protect(
    rules_file: str | Path | None = None,
    agent_id: str | None = None,
    server_url: str | None = None
) -> ProtectEngine:
    """
    Initialize the global protection engine with automatic configuration.

    This function auto-discovers rules and registers with the Agent Protect server.

    Usage:
        # Simplest - auto-discovers everything
        init_protect()

        # With custom agent ID
        init_protect(agent_id="my-custom-agent")

        # With explicit rules file
        init_protect(rules_file="custom_rules.yaml")

        # With custom server
        init_protect(server_url="https://protect.example.com")

    Args:
        rules_file: Optional path to YAML rules file. If not provided, auto-discovers
                   rules.yaml in the calling file's directory, CWD, or parent dir.
                   If not found, fetches rules from server.
        agent_id: Optional agent identifier. If not provided, generates one based
                 on the calling file name and process ID.
        server_url: Optional server URL. If not provided, uses AGENT_PROTECT_URL
                   environment variable or defaults to http://localhost:8000

    Returns:
        Initialized protection engine

    Environment Variables:
        AGENT_PROTECT_URL: Server URL (default: http://localhost:8000)
        AGENT_ID: Agent identifier (optional)
    """
    global _protect_engine

    # Allow environment variables to override
    agent_id = agent_id or os.getenv('AGENT_ID')
    server_url = server_url or os.getenv('AGENT_PROTECT_URL')

    _protect_engine = ProtectEngine(
        rules_file=rules_file,
        agent_id=agent_id,
        server_url=server_url,
        auto_discover=True
    )

    return _protect_engine


# Backward compatibility alias
def init_protect_engine(rules_file: str | Path) -> ProtectEngine:
    """
    Legacy initialization function.

    Deprecated: Use init_protect() instead for automatic configuration.

    Args:
        rules_file: Path to the YAML rules file

    Returns:
        Initialized protection engine
    """
    return init_protect(rules_file=rules_file)


def get_protect_engine() -> ProtectEngine | None:
    """Get the global protection engine instance."""
    return _protect_engine


def protect(step_id: str, **data_sources):
    """
    Decorator to apply protection rules at a specific step.

    Args:
        step_id: The step identifier to match against rules
        **data_sources: Named arguments specifying what data to extract
            Maps data types (input, output, context, etc.) to function parameter names.

            The decorator introspects function arguments and extracts values based on
            this mapping. For example:
            - input='user_text' means: extract the 'user_text' parameter as 'input' data
            - context='ctx' means: extract the 'ctx' parameter as 'context' data
            - output='result' means: extract the return value as 'output' data (special case)

    Example:
        @protect('input-validation', input='user_input', context='ctx')
        async def process_input(user_input: str, ctx: dict):
            # Protection rules are automatically enforced
            # 'user_input' is checked as 'input'
            # 'ctx' is checked as 'context'
            return f"Processed: {user_input}"

        # When you call:
        await process_input("Hello", {"user_id": "123"})

        # The decorator extracts:
        # data = {
        #     'input': "Hello",           # from user_input parameter
        #     'context': {"user_id": "123"}  # from ctx parameter
        # }

    What Information Is Available:
        Before function execution:
        - All function parameters mapped via data_sources
        - Can check: input, context, metadata, messages, etc.

        After function execution (if output is mapped):
        - The return value of the function
        - Can check: output, tool_results, etc.

    Raises:
        RuleViolation: If a deny rule is triggered
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            engine = get_protect_engine()

            if engine is None:
                # No engine initialized, skip enforcement
                return await func(*args, **kwargs)

            # Extract data from function arguments
            data = _extract_data(func, args, kwargs, data_sources)

            # Evaluate rules BEFORE function execution
            if any(k in data for k in ['input', 'context', 'metadata', 'messages']):
                try:
                    result = engine.evaluate_rule(step_id, data)
                    if result['action'] == 'warn':
                        print(f"⚠️  Warning: {result['message']}")
                except RuleViolation as e:
                    print(f"🚫 Rule violation: {e.message}")
                    raise

            # Execute the function
            output = await func(*args, **kwargs)

            # Evaluate rules AFTER function execution (for output checks)
            if 'output' in data_sources:
                data['output'] = output
                try:
                    result = engine.evaluate_rule(step_id, data)

                    if result['action'] == 'redact':
                        # Return redacted output
                        return result['data']
                    elif result['action'] == 'warn':
                        print(f"⚠️  Warning: {result['message']}")
                except RuleViolation as e:
                    print(f"🚫 Rule violation in output: {e.message}")
                    raise

            return output

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            engine = get_protect_engine()

            if engine is None:
                return func(*args, **kwargs)

            data = _extract_data(func, args, kwargs, data_sources)

            if any(k in data for k in ['input', 'context', 'metadata', 'messages']):
                try:
                    result = engine.evaluate_rule(step_id, data)
                    if result['action'] == 'warn':
                        print(f"⚠️  Warning: {result['message']}")
                except RuleViolation as e:
                    print(f"🚫 Rule violation: {e.message}")
                    raise

            output = func(*args, **kwargs)

            if 'output' in data_sources:
                data['output'] = output
                try:
                    result = engine.evaluate_rule(step_id, data)

                    if result['action'] == 'redact':
                        return result['data']
                    elif result['action'] == 'warn':
                        print(f"⚠️  Warning: {result['message']}")
                except RuleViolation as e:
                    print(f"🚫 Rule violation in output: {e.message}")
                    raise

            return output

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _extract_data(
    func: Callable,
    args: tuple,
    kwargs: dict,
    data_sources: dict[str, str]
) -> dict[str, Any]:
    """
    Extract data from function arguments based on data_sources mapping.

    Args:
        func: The function being decorated
        args: Positional arguments
        kwargs: Keyword arguments
        data_sources: Mapping of data types to parameter names

    Returns:
        Dictionary of extracted data
    """
    import inspect

    data = {}
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    for data_type, param_name in data_sources.items():
        if param_name in bound.arguments:
            data[data_type] = bound.arguments[param_name]

    return data

