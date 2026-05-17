"""
Hybrid Chatbot: Main Application Entry Point
Integrates semantic routing with SQL and Vector pipelines for intelligent query processing.
Supports both OpenAI and Azure OpenAI APIs.
"""

import os
import sys
import logging
from typing import Optional
from pathlib import Path

# Load environment variables from .env file BEFORE importing Config
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import openai
from openai import AzureOpenAI
from core.config import Config
from core.router import QueryClassifier, QueryRoute
from core.state import ConversationState
from pipelines.sql_pipeline import SQLPipeline
from pipelines.vector_pipeline import VectorPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_llm_client():
    """
    Create and return the appropriate LLM client based on configuration.
    
    Returns:
        openai.Client or AzureOpenAI: Configured LLM client
    """
    if Config.LLM_PROVIDER == "azure":
        logger.info("Initializing Azure OpenAI client")
        client = AzureOpenAI(
            api_key=Config.AZURE_OPENAI_API_KEY,
            api_version=Config.AZURE_API_VERSION,
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
        )
        logger.info(f"Azure OpenAI client initialized (deployment: {Config.AZURE_OPENAI_DEPLOYMENT})")
        return client
    else:
        logger.info("Initializing OpenAI client")
        client = openai.Client(api_key=Config.OPENAI_API_KEY)
        logger.info(f"OpenAI client initialized (model: {Config.OPENAI_MODEL})")
        return client


def get_model_name() -> str:
    """Get the appropriate model name based on LLM provider."""
    if Config.LLM_PROVIDER == "azure":
        return Config.AZURE_OPENAI_DEPLOYMENT
    else:
        return Config.OPENAI_MODEL


class HybridChatbot:
    """
    Main chatbot class that orchestrates routing and pipeline execution.
    
    Architecture:
    1. Query Router: Semantic classification of incoming queries
    2. SQL Pipeline: Structured data retrieval and aggregation
    3. Vector Pipeline: Unstructured data retrieval via RAG
    4. State Management: Multi-turn conversation tracking
    """
    
    def __init__(self):
        """Initialize the Hybrid Chatbot with all components."""
        try:
            # Validate configuration
            Config.validate()
            logger.info("Configuration validated successfully")
            logger.info(f"LLM Provider: {Config.LLM_PROVIDER}")
            
            # Initialize LLM client
            self.client = create_llm_client()
            self.model_name = get_model_name()
            
            # Initialize core components
            self.classifier = QueryClassifier(
                client=self.client,
                model=self.model_name
            )
            logger.info("Query Classifier initialized")
            
            self.sql_pipeline = SQLPipeline(
                db_path=Config.DB_PATH,
                client=self.client,
                model=self.model_name
            )
            logger.info(f"SQL Pipeline initialized (db: {Config.DB_PATH})")
            
            self.vector_pipeline = VectorPipeline(
                client=self.client,
                model=self.model_name
            )
            logger.info("Vector Pipeline initialized")
            
            # Initialize conversation state
            self.state = ConversationState(max_history=20)
            logger.info("Conversation State initialized")
            
            logger.info("=" * 60)
            logger.info("Hybrid Chatbot successfully initialized")
            logger.info(f"Configuration: {Config.to_dict()}")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"Failed to initialize chatbot: {e}")
            raise
    
    def _process_sql_route(self, user_input: str) -> str:
        """
        Process query through SQL pipeline.
        
        Args:
            user_input: User's query string
            
        Returns:
            str: Response from SQL pipeline
        """
        logger.debug("Routing to SQL Pipeline")
        response = self.sql_pipeline.run(user_input)
        return response
    
    def _process_vector_route(self, user_input: str) -> str:
        """
        Process query through Vector pipeline.
        
        Args:
            user_input: User's query string
            
        Returns:
            str: Response from Vector pipeline
        """
        logger.debug("Routing to Vector Pipeline")
        response = self.vector_pipeline.run(user_input)
        return response
    
    def _process_unknown_route(self, user_input: str) -> str:
        """
        Handle unknown/ambiguous queries.
        
        Args:
            user_input: User's query string
            
        Returns:
            str: Helpful error message
        """
        logger.warning("Unable to classify query")
        return (
            "I'm sorry, I couldn't determine how to process your request. "
            "Please try rephrasing your question. I can help with:\n"
            "- Structured data questions (e.g., 'How many orders last month?')\n"
            "- Policy and FAQ questions (e.g., 'What is your refund policy?')"
        )
    
    def chat(self, user_input: str, context_aware: bool = False) -> str:
        """
        Process a user query and return a response.
        
        Args:
            user_input: The user's input query
            context_aware: Whether to use conversation history for routing
            
        Returns:
            str: The chatbot's response
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Turn {self.state.turn_count + 1}: Processing query")
        logger.info(f"Query: {user_input}")
        
        try:
            # Add user message to state
            self.state.add_message(role="user", content=user_input)
            
            # Step 1: Classify query with semantic router
            logger.debug("Step 1: Query classification")
            if context_aware and len(self.state) > 1:
                decision = self.classifier.classify_with_context(
                    query=user_input,
                    conversation_history=self.state.get_conversation_history()
                )
            else:
                decision = self.classifier.classify(user_input)
            
            # Log routing decision
            logger.info(f"[Router] Route: {decision.route.value.upper()}")
            logger.info(f"[Router] Confidence: {decision.confidence:.2f}")
            logger.info(f"[Router] Reasoning: {decision.reasoning}")
            
            # Step 2: Execute appropriate pipeline
            logger.debug("Step 2: Pipeline execution")
            if decision.route == QueryRoute.SQL:
                response = self._process_sql_route(user_input)
            elif decision.route == QueryRoute.VECTOR:
                response = self._process_vector_route(user_input)
            else:
                response = self._process_unknown_route(user_input)
            
            # Add assistant response to state
            self.state.add_message(
                role="assistant",
                content=response,
                metadata={
                    "route": decision.route.value,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning
                }
            )
            
            logger.info(f"Response generated successfully")
            logger.info(f"{'='*60}\n")
            
            return response
        
        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            logger.error(error_message)
            
            # Add error to state for context
            self.state.add_message(role="assistant", content=error_message)
            
            return error_message
    
    def get_conversation_history(self) -> list:
        """Get the current conversation history."""
        return self.state.get_conversation_history()
    
    def clear_history(self) -> None:
        """Clear conversation history and reset state."""
        self.state.clear_history()
        logger.info("Conversation history cleared")
    
    def __repr__(self) -> str:
        return (
            f"HybridChatbot("
            f"state={self.state}, "
            f"model={self.model_name})"
        )


def main():
    """Main CLI interface for the Hybrid Chatbot."""
    print("\n" + "="*60)
    print("HYBRID CHATBOT - Production Architecture Demo")
    print("="*60)
    print("\nThis chatbot demonstrates:")
    print("✓ Semantic query routing (LLM-based classification)")
    print("✓ SQL Pipeline (structured data with injection protection)")
    print("✓ Vector Pipeline (RAG for unstructured data)")
    print("✓ Multi-turn conversation state management")
    print("✓ Defensive programming and error handling")
    print("\nType 'exit' or 'quit' to end conversation")
    print("Type 'history' to see conversation history")
    print("Type 'clear' to clear conversation state")
    print("="*60 + "\n")
    
    try:
        # Initialize chatbot
        bot = HybridChatbot()
        
        # Interactive CLI loop
        while True:
            try:
                user_query = input("\nYou: ").strip()
                
                if not user_query:
                    continue
                
                # Handle special commands
                if user_query.lower() in ['exit', 'quit']:
                    print("\nBot: Thank you for using the Hybrid Chatbot. Goodbye!")
                    break
                
                if user_query.lower() == 'history':
                    history = bot.get_conversation_history()
                    print("\n[Conversation History]")
                    for i, msg in enumerate(history, 1):
                        print(f"{i}. {msg['role'].upper()}: {msg['content'][:100]}...")
                    continue
                
                if user_query.lower() == 'clear':
                    bot.clear_history()
                    print("\nBot: Conversation history cleared.")
                    continue
                
                # Process query
                response = bot.chat(user_query, context_aware=True)
                print(f"\nBot: {response}")
            
            except KeyboardInterrupt:
                print("\n\nBot: Conversation interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in CLI loop: {e}")
                print(f"\nBot: An error occurred: {e}")
    
    except Exception as e:
        logger.error(f"Failed to start chatbot: {e}")
        print(f"\nError: Failed to initialize chatbot: {e}")
        print("\nPlease ensure:")
        
        if Config.LLM_PROVIDER == "openai":
            print("- OPENAI_API_KEY environment variable is set")
            print("  Example: export OPENAI_API_KEY=sk-your-api-key")
        elif Config.LLM_PROVIDER == "azure":
            print("- AZURE_OPENAI_API_KEY environment variable is set")
            print("- AZURE_OPENAI_ENDPOINT environment variable is set")
            print("- AZURE_OPENAI_DEPLOYMENT environment variable is set")
            print("\n  Example for Azure:")
            print("  export LLM_PROVIDER=azure")
            print("  export AZURE_OPENAI_API_KEY=your-api-key")
            print("  export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
            print("  export AZURE_OPENAI_DEPLOYMENT=your-deployment-name")
        else:
            print(f"- Valid LLM_PROVIDER value: {Config.LLM_PROVIDER} is invalid")
        
        print("\n- data/mock_db.sqlite exists (run: python scripts/init_db.py)")
        sys.exit(1)


if __name__ == "__main__":
    main()
