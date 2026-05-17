"""
Intelligent Query Classifier (Router) using LLM-based semantic understanding.
Routes queries to SQL or Vector pipelines based on semantic analysis.
"""

from enum import Enum
import json
from typing import Optional
from pydantic import BaseModel, Field
import openai
import logging

logger = logging.getLogger(__name__)


class QueryRoute(str, Enum):
    """Enumeration of available routing destinations."""
    SQL = "sql"
    VECTOR = "vector"
    UNKNOWN = "unknown"


class RouteDecision(BaseModel):
    """Structured output for routing decisions."""
    route: QueryRoute = Field(
        description="The routed destination for the query. 'sql' for structured data/metrics, 'vector' for policies/FAQs/unstructured text."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    reasoning: str = Field(
        description="Brief justification for the routing decision (max 200 chars)"
    )


class QueryClassifier:
    """
    LLM-based semantic router that classifies queries into SQL or Vector pipelines.
    Uses Pydantic-enforced JSON schema for deterministic, type-safe routing.
    """
    
    SYSTEM_PROMPT = """
    You are a highly precise semantic router for a hybrid chatbot system. Your job is to classify 
    user queries into one of two categories:
    
    1. 'sql': Queries requesting structured data, metrics, counts, specific customer records, 
       financial aggregations, or database queries.
       Examples: 
       - "Total orders last month?"
       - "Top 5 customers by spending"
       - "How many customers are in Europe?"
       - "Orders placed in Q4 2024"
    
    2. 'vector': Queries requesting explanations, policies, FAQs, unstructured product information, 
       or general knowledge questions.
       Examples:
       - "What is your refund policy?"
       - "Explain product features of X"
       - "Tell me about orders policy"
       - "How does the return process work?"
    
    CRITICAL ROUTING RULES:
    - "Tell me about orders policy" → vector (asking for policy explanation, not metrics)
    - "Customers with refund issues" → vector (asking for support/help context)
    - Mixed queries that emphasize policy/explanation → vector
    - Mixed queries that emphasize metrics/counts → sql
    
    Return high confidence (>0.9) when classification is clear.
    Return medium confidence (0.6-0.9) when there are multiple possible interpretations.
    Return low confidence (<0.6) only in truly ambiguous cases.
    
    Always provide clear reasoning for your decision.
    Return only valid JSON, with keys: route, confidence, reasoning.
    Do not include any additional text or markdown.
    """
    
    def __init__(self, client: openai.Client, model: str = "gpt-4o"):
        """
        Initialize the Query Classifier.
        
        Args:
            client: OpenAI API client instance
            model: Model to use for classification (default: gpt-4o)
        """
        self.client = client
        self.model = model
    
    def _parse_response(self, raw_text: str) -> RouteDecision:
        """
        Parse JSON output from the LLM router.

        Args:
            raw_text: Raw text response from the model

        Returns:
            RouteDecision: Parsed routing decision
        """

        clean_text = raw_text.strip()
        clean_text = clean_text.strip("`\n ")
        if clean_text.startswith("json"):
            clean_text = clean_text[len("json"):].strip()

        try:
            parsed = json.loads(clean_text)
            return RouteDecision(**parsed)
        except Exception as e:
            logger.error(f"Failed to parse routing response: {e}. Raw response: {raw_text}")
            raise


    def classify(self, query: str) -> RouteDecision:
        """
        Classify a user query to determine the appropriate pipeline.
        
        Args:
            query: The user's input query string
            
        Returns:
            RouteDecision: Structured routing decision with route, confidence, and reasoning
        """
        try:
            logger.debug(f"Classifying query: {query}")
            
            # Use OpenAI's structured output via beta API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.0,
                max_tokens=150,
                stop=None
            )

            raw_text = response.choices[0].message.content.strip()
            decision = self._parse_response(raw_text)
            logger.info(f"Query routed to {decision.route.value} with confidence {decision.confidence}")
            
            return decision
            
        except Exception as e:
            # Fallback to UNKNOWN route on API failure
            logger.error(f"Classification failed: {e}. Falling back to UNKNOWN route.")
            return RouteDecision(
                route=QueryRoute.UNKNOWN,
                confidence=0.0,
                reasoning=f"Classifier error: {str(e)[:100]}"
            )
    
    def classify_with_context(
        self, 
        query: str, 
        conversation_history: Optional[list] = None
    ) -> RouteDecision:
        """
        Classify a query considering prior conversation context.
        
        Args:
            query: The current user query
            conversation_history: List of prior messages for context
            
        Returns:
            RouteDecision: Routing decision informed by conversation history
        """
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        # Add conversation history for context
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": query})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=150,
                stop=None
            )

            raw_text = response.choices[0].message.content.strip()
            return self._parse_response(raw_text)
            
        except Exception as e:
            logger.error(f"Context-aware classification failed: {e}")
            return RouteDecision(
                route=QueryRoute.UNKNOWN,
                confidence=0.0,
                reasoning=f"Classifier error: {str(e)[:100]}"
            )
