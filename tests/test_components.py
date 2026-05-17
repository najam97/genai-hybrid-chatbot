"""
Unit Tests for Hybrid Chatbot Components
Demonstrates testing best practices with dependency injection.

Run with: pytest tests/ -v
"""

import pytest
import sqlite3
from unittest.mock import Mock, MagicMock, patch
from io import StringIO

# Import components to test
from core.router import QueryClassifier, QueryRoute, RouteDecision
from core.config import Config
from core.state import ConversationState, Message
from pipelines.sql_pipeline import SQLPipeline
from pipelines.vector_pipeline import VectorPipeline


class TestQueryClassifier:
    """Test the semantic query router."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock OpenAI client for testing."""
        return Mock()
    
    @pytest.fixture
    def classifier(self, mock_client):
        """Create classifier with mock client."""
        return QueryClassifier(client=mock_client, model="gpt-4o-mini")
    
    def test_classify_sql_query(self, classifier, mock_client):
        """Test classification of SQL query."""
        # Mock API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = RouteDecision(
            route=QueryRoute.SQL,
            confidence=0.95,
            reasoning="Asking for metrics"
        )
        mock_client.beta.chat.completions.parse.return_value = mock_response
        
        result = classifier.classify("How many orders last month?")
        
        assert result.route == QueryRoute.SQL
        assert result.confidence == 0.95
        assert "metrics" in result.reasoning.lower()
    
    def test_classify_vector_query(self, classifier, mock_client):
        """Test classification of vector/policy query."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = RouteDecision(
            route=QueryRoute.VECTOR,
            confidence=0.96,
            reasoning="Asking for policy information"
        )
        mock_client.beta.chat.completions.parse.return_value = mock_response
        
        result = classifier.classify("What is your refund policy?")
        
        assert result.route == QueryRoute.VECTOR
        assert result.confidence == 0.96
    
    def test_classify_api_failure_fallback(self, classifier, mock_client):
        """Test fallback to UNKNOWN route on API failure."""
        mock_client.beta.chat.completions.parse.side_effect = Exception("API Error")
        
        result = classifier.classify("Some query")
        
        assert result.route == QueryRoute.UNKNOWN
        assert result.confidence == 0.0
        assert "error" in result.reasoning.lower()


class TestConversationState:
    """Test multi-turn conversation state management."""
    
    @pytest.fixture
    def state(self):
        """Create fresh conversation state."""
        return ConversationState(max_history=10)
    
    def test_add_message(self, state):
        """Test adding messages to conversation."""
        state.add_message(role="user", content="Hello")
        state.add_message(role="assistant", content="Hi there!")
        
        assert len(state) == 2
        assert state.turn_count == 1  # Only one user message
    
    def test_get_last_user_message(self, state):
        """Test retrieval of most recent user message."""
        state.add_message(role="user", content="First question")
        state.add_message(role="assistant", content="Answer")
        state.add_message(role="user", content="Second question")
        
        last_user = state.get_last_user_message()
        assert last_user == "Second question"
    
    def test_conversation_history_format(self, state):
        """Test conversation history in OpenAI API format."""
        state.add_message(role="user", content="Question 1")
        state.add_message(role="assistant", content="Answer 1")
        
        history = state.get_conversation_history()
        
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Question 1"}
        assert history[1] == {"role": "assistant", "content": "Answer 1"}
    
    def test_max_history_trimming(self):
        """Test that old messages are trimmed when max_history exceeded."""
        state = ConversationState(max_history=3)
        
        # Add 5 messages
        for i in range(5):
            state.add_message(role="user" if i % 2 == 0 else "assistant", 
                            content=f"Message {i}")
        
        # Should only keep last 3
        assert len(state) == 3
        assert state.get_last_user_message() == "Message 4"
    
    def test_context_variables(self, state):
        """Test context variable storage across turns."""
        state.set_context_variable("selected_date", "2024-Q1")
        assert state.get_context_variable("selected_date") == "2024-Q1"
        assert state.get_context_variable("missing", "default") == "default"
    
    def test_clear_history(self, state):
        """Test clearing all conversation state."""
        state.add_message(role="user", content="Test")
        state.set_context_variable("key", "value")
        
        state.clear_history()
        
        assert len(state) == 0
        assert state.turn_count == 0
        assert state.get_context_variable("key") is None


class TestSQLPipeline:
    """Test SQL pipeline security and functionality."""
    
    @pytest.fixture
    def mock_client(self):
        return Mock()
    
    @pytest.fixture
    def pipeline(self, mock_client, tmp_path):
        """Create pipeline with temporary test database."""
        db_path = str(tmp_path / "test.db")
        # Create minimal test database
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE customers (id INTEGER, name TEXT)")
        conn.commit()
        conn.close()
        
        return SQLPipeline(db_path=db_path, client=mock_client)
    
    def test_safe_select_query(self, pipeline):
        """Test that SELECT queries are allowed."""
        assert pipeline._is_safe_query("SELECT * FROM customers")
        assert pipeline._is_safe_query("SELECT id, name FROM customers WHERE id = 1")
        assert pipeline._is_safe_query("SELECT COUNT(*) FROM customers")
    
    def test_unsafe_delete_query(self, pipeline):
        """Test that DELETE queries are blocked."""
        assert not pipeline._is_safe_query("DELETE FROM customers")
        assert not pipeline._is_safe_query("DELETE FROM customers WHERE id = 1")
    
    def test_unsafe_drop_query(self, pipeline):
        """Test that DROP queries are blocked."""
        assert not pipeline._is_safe_query("DROP TABLE customers")
    
    def test_unsafe_insert_query(self, pipeline):
        """Test that INSERT queries are blocked."""
        assert not pipeline._is_safe_query("INSERT INTO customers VALUES (1, 'John')")
    
    def test_unsafe_update_query(self, pipeline):
        """Test that UPDATE queries are blocked."""
        assert not pipeline._is_safe_query("UPDATE customers SET name = 'Jane'")
    
    def test_query_must_start_with_select(self, pipeline):
        """Test that non-SELECT queries are rejected."""
        assert not pipeline._is_safe_query("WITH cte AS (SELECT * FROM customers) SELECT * FROM cte")
        # This would still start with WITH, not SELECT in the strict check
    
    def test_comment_removal_before_validation(self, pipeline):
        """Test that SQL comments are ignored during validation."""
        # Comments should be removed before checking for unsafe keywords
        query = "-- This is a comment\nSELECT * FROM customers"
        assert pipeline._is_safe_query(query)


class TestVectorPipeline:
    """Test vector pipeline hallucination prevention."""
    
    @pytest.fixture
    def mock_client(self):
        return Mock()
    
    @pytest.fixture
    def pipeline(self, mock_client):
        """Create vector pipeline with mock client."""
        return VectorPipeline(client=mock_client)
    
    def test_retrieve_documents(self, pipeline):
        """Test document retrieval from knowledge base."""
        docs = pipeline._retrieve_documents("refund policy", top_k=3)
        
        assert len(docs) <= 3
        assert all("title" in doc and "content" in doc for doc in docs)
    
    def test_empty_retrieval_handling(self, pipeline):
        """Test handling when no documents match query."""
        docs = pipeline._retrieve_documents("xyzabc123notfound", top_k=3)
        assert len(docs) == 0
    
    def test_hallucination_prevention_instruction(self, pipeline, mock_client):
        """Test that generation prompt includes hallucination prevention."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "I do not have enough information"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = pipeline._generate_response(
            "Unknown question",
            "Some context"
        )
        
        # Verify the API was called
        mock_client.chat.completions.create.assert_called_once()
        
        # Check that the call included anti-hallucination instructions
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "not hallucinate" in prompt.lower() or "do not" in prompt.lower()


class TestConfig:
    """Test configuration management."""
    
    def test_config_validation_missing_key(self):
        """Test that Config.validate() fails without API key."""
        original_key = Config.OPENAI_API_KEY
        Config.OPENAI_API_KEY = ""
        
        with pytest.raises(ValueError):
            Config.validate()
        
        Config.OPENAI_API_KEY = original_key  # Restore
    
    def test_config_to_dict(self):
        """Test configuration export to dictionary."""
        config_dict = Config.to_dict()
        
        assert "openai_model" in config_dict
        assert "db_path" in config_dict
        assert "db_read_only" in config_dict


# Run tests with: pytest tests/ -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
