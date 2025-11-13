"""
Tests for the LangGraph agent with Agent Protect integration.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage
from agent import (
    AgentState,
    safety_check_node,
    should_continue,
    reject_node,
    agent_node,
    create_graph,
    run_agent,
)


class TestSafetyCheckNode:
    """Tests for the safety check node."""

    @pytest.mark.asyncio
    async def test_safety_check_no_messages(self):
        """Test safety check with empty message list."""
        state = {"messages": [], "safety_check_passed": True, "safety_reason": ""}
        result = await safety_check_node(state)
        
        assert result["safety_check_passed"] is True
        assert result["safety_reason"] == "No user input to check"

    @pytest.mark.asyncio
    async def test_safety_check_non_human_message(self):
        """Test safety check with non-human message."""
        state = {
            "messages": [AIMessage(content="Hello")],
            "safety_check_passed": True,
            "safety_reason": ""
        }
        result = await safety_check_node(state)
        
        assert result["safety_check_passed"] is True
        assert result["safety_reason"] == "No user input to check"

    @pytest.mark.asyncio
    @patch("agent.AGENT_PROTECT_AVAILABLE", False)
    async def test_safety_check_no_protection(self):
        """Test safety check when Agent Protect is not available."""
        state = {
            "messages": [HumanMessage(content="Hello")],
            "safety_check_passed": True,
            "safety_reason": ""
        }
        result = await safety_check_node(state)
        
        assert result["safety_check_passed"] is True
        assert result["safety_reason"] == "Agent Protect not configured"

    @pytest.mark.asyncio
    @patch("agent.AGENT_PROTECT_AVAILABLE", True)
    @patch("agent.AgentProtectClient")
    async def test_safety_check_safe_content(self, mock_client_class):
        """Test safety check with safe content."""
        # Mock the client and result
        mock_result = MagicMock()
        mock_result.is_safe = True
        mock_result.reason = "Content is safe"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.check_protection.return_value = mock_result
        mock_client_class.return_value = mock_client
        
        state = {
            "messages": [HumanMessage(content="Hello, how are you?")],
            "safety_check_passed": True,
            "safety_reason": ""
        }
        result = await safety_check_node(state)
        
        assert result["safety_check_passed"] is True
        assert result["safety_reason"] == "Content is safe"

    @pytest.mark.asyncio
    @patch("agent.AGENT_PROTECT_AVAILABLE", True)
    @patch("agent.AgentProtectClient")
    async def test_safety_check_unsafe_content(self, mock_client_class):
        """Test safety check with unsafe content."""
        # Mock the client and result
        mock_result = MagicMock()
        mock_result.is_safe = False
        mock_result.reason = "Content contains inappropriate language"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.check_protection.return_value = mock_result
        mock_client_class.return_value = mock_client
        
        state = {
            "messages": [HumanMessage(content="Unsafe content")],
            "safety_check_passed": True,
            "safety_reason": ""
        }
        result = await safety_check_node(state)
        
        assert result["safety_check_passed"] is False
        assert "inappropriate language" in result["safety_reason"]


class TestShouldContinue:
    """Tests for the conditional routing function."""

    def test_should_continue_safe(self):
        """Test routing when content is safe."""
        state = {"safety_check_passed": True}
        result = should_continue(state)
        assert result == "process"

    def test_should_continue_unsafe(self):
        """Test routing when content is unsafe."""
        state = {"safety_check_passed": False}
        result = should_continue(state)
        assert result == "reject"

    def test_should_continue_default(self):
        """Test routing with default state."""
        state = {}
        result = should_continue(state)
        assert result == "process"


class TestRejectNode:
    """Tests for the reject node."""

    def test_reject_with_reason(self):
        """Test rejection with a specific reason."""
        state = {
            "messages": [HumanMessage(content="Test")],
            "safety_check_passed": False,
            "safety_reason": "Contains inappropriate content"
        }
        result = reject_node(state)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert "inappropriate content" in result["messages"][0].content.lower()

    def test_reject_default_reason(self):
        """Test rejection with default reason."""
        state = {
            "messages": [HumanMessage(content="Test")],
            "safety_check_passed": False
        }
        result = reject_node(state)
        
        assert "messages" in result
        assert "safety checks" in result["messages"][0].content.lower()


class TestAgentNode:
    """Tests for the agent processing node."""

    @pytest.mark.asyncio
    @patch("agent.ChatOpenAI")
    async def test_agent_node(self, mock_chat_class):
        """Test the agent node processes messages."""
        # Mock the LLM
        mock_response = AIMessage(content="I'm here to help!")
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm
        
        state = {
            "messages": [HumanMessage(content="Hello!")],
            "safety_check_passed": True,
            "safety_reason": ""
        }
        result = await agent_node(state)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "I'm here to help!"


class TestGraph:
    """Tests for the complete graph."""

    def test_create_graph(self):
        """Test that the graph is created successfully."""
        graph = create_graph()
        assert graph is not None

    @pytest.mark.asyncio
    @patch("agent.AGENT_PROTECT_AVAILABLE", False)
    @patch("agent.ChatOpenAI")
    async def test_run_agent(self, mock_chat_class):
        """Test running the agent end-to-end."""
        # Mock the LLM
        mock_response = AIMessage(content="Hello! How can I help you today?")
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm
        
        response = await run_agent("Hello!")
        
        assert response == "Hello! How can I help you today?"


class TestIntegration:
    """Integration tests for the complete workflow."""

    @pytest.mark.asyncio
    @patch("agent.AGENT_PROTECT_AVAILABLE", True)
    @patch("agent.AgentProtectClient")
    @patch("agent.ChatOpenAI")
    async def test_full_workflow_safe_input(self, mock_chat_class, mock_client_class):
        """Test the complete workflow with safe input."""
        # Mock Agent Protect
        mock_result = MagicMock()
        mock_result.is_safe = True
        mock_result.reason = "Content is safe"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.check_protection.return_value = mock_result
        mock_client_class.return_value = mock_client
        
        # Mock LLM
        mock_response = AIMessage(content="Sure, I can help with that!")
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm
        
        response = await run_agent("Can you help me?")
        
        assert response == "Sure, I can help with that!"

    @pytest.mark.asyncio
    @patch("agent.AGENT_PROTECT_AVAILABLE", True)
    @patch("agent.AgentProtectClient")
    @patch("agent.ChatOpenAI")
    async def test_full_workflow_unsafe_input(self, mock_chat_class, mock_client_class):
        """Test the complete workflow with unsafe input."""
        # Mock Agent Protect to reject
        mock_result = MagicMock()
        mock_result.is_safe = False
        mock_result.reason = "Inappropriate content detected"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.check_protection.return_value = mock_result
        mock_client_class.return_value = mock_client
        
        # Mock LLM (should not be called)
        mock_chat_class.return_value = AsyncMock()
        
        response = await run_agent("Unsafe message")
        
        assert "sorry" in response.lower()
        assert "inappropriate content" in response.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

