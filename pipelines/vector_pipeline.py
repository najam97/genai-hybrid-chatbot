"""
Vector Pipeline: RAG (Retrieval-Augmented Generation) for unstructured data.
Retrieves relevant documents and generates grounded responses.
"""

import openai
import logging
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)


class VectorPipeline:
    """
    Processes unstructured data queries using RAG (Retrieval-Augmented Generation).
    Retrieves relevant documents and uses LLM to generate grounded responses.
    """
    
    # Mock knowledge base - in production, this would be a real vector database
    MOCK_KNOWLEDGE_BASE = [
        {
            "id": 1,
            "title": "Return Policy",
            "content": "Our return policy allows refunds within 30 days of purchase. Items must be in original condition with all packaging. Refunds are processed within 5-7 business days after we receive the returned item."
        },
        {
            "id": 2,
            "title": "Shipping Information",
            "content": "We offer free shipping on orders over $50. Standard shipping takes 5-7 business days. Express shipping (2-3 days) is available for an additional fee. All orders include tracking information."
        },
        {
            "id": 3,
            "title": "Product Features",
            "content": "Our premium product line features advanced cooling technology, water resistance up to 100 meters, and a battery life of up to 7 days. All products come with a 2-year manufacturer warranty."
        },
        {
            "id": 4,
            "title": "Customer Support",
            "content": "Contact us via email at support@company.com or call 1-800-SUPPORT. Our support team is available Monday-Friday, 9 AM - 5 PM EST. Response time is typically within 24 hours."
        },
        {
            "id": 5,
            "title": "Warranty Information",
            "content": "All products include a 2-year limited warranty covering manufacturing defects. Extended warranty plans are available for purchase at checkout. Warranty does not cover accidental damage or normal wear and tear."
        },
        {
            "id": 6,
            "title": "Order Policy",
            "content": "Orders are processed within 24 hours of placement. You will receive an order confirmation email with tracking information. Orders cannot be modified after they enter the fulfillment stage. Cancellations are accepted up to 12 hours after order placement."
        },
        {
            "id": 7,
            "title": "Payment Methods",
            "content": "We accept all major credit cards (Visa, Mastercard, American Express), PayPal, and bank transfers. All payments are processed securely using industry-standard encryption. Payment information is never stored on our servers."
        }
    ]
    
    def __init__(
        self, 
        client: openai.Client, 
        model: str = "gpt-4o",
        vector_db=None,
        knowledge_base: Optional[List[Dict]] = None
    ):
        """
        Initialize the Vector Pipeline.
        
        Args:
            client: OpenAI API client instance
            model: Model to use for generation (default: gpt-4o)
            vector_db: Vector database instance (FAISS, Pinecone, etc.)
            knowledge_base: Custom knowledge base (defaults to mock)
        """
        self.client = client
        self.model = model
        self.vector_db = vector_db
        self.knowledge_base = knowledge_base or self.MOCK_KNOWLEDGE_BASE
    
    def _retrieve_documents(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieve relevant documents from knowledge base.
        
        In production, this would use a real vector database with embeddings.
        For now, we use a simple keyword-based retrieval.
        
        Args:
            query: User query string
            top_k: Number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        logger.debug(f"Retrieving documents for query: {query}")
        
        # Keyword-based retrieval (fallback for mock database)
        # In production, use embeddings-based semantic search
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_docs = []
        for doc in self.knowledge_base:
            title_lower = doc["title"].lower()
            content_lower = doc["content"].lower()
            
            # Simple scoring based on keyword overlap
            title_score = sum(1 for word in query_words if word in title_lower)
            content_score = sum(1 for word in query_words if word in content_lower)
            
            score = (title_score * 2) + content_score  # Title matches weighted more
            
            if score > 0:
                scored_docs.append((doc, score))
        
        # Sort by score and return top_k
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        retrieved = [doc for doc, _ in scored_docs[:top_k]]
        
        logger.info(f"Retrieved {len(retrieved)} documents")
        
        return retrieved
    
    def _generate_response(self, query: str, context: str) -> str:
        """
        Generate a natural language response using LLM.
        
        Args:
            query: User's question
            context: Retrieved context from knowledge base
            
        Returns:
            str: Generated response
        """
        prompt = f"""
You are a helpful customer support assistant. You must answer the user's question ONLY using the provided context.

CRITICAL RULES:
1. Answer based strictly on the provided context
2. Do not make up information not in the context
3. If the answer is not in the context, clearly state: "I do not have enough information to answer that question. Please contact our support team."
4. Be concise but helpful
5. Use friendly, professional language
6. Quote relevant parts of the context when helpful

Context:
{context}

User Question: {query}

Provide your answer now:
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Low temperature for factual grounding
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            raise ValueError(f"Response generation error: {str(e)}")
    
    def run(self, user_query: str) -> str:
        """
        Execute the Vector pipeline end-to-end.
        
        Args:
            user_query: Natural language question about unstructured data
            
        Returns:
            str: Natural language response with context grounding
        """
        logger.info(f"Vector Pipeline: Processing query: {user_query}")
        
        try:
            # Step 1: Retrieve relevant documents
            logger.debug("Step 1: Retrieving relevant documents")
            retrieved_docs = self._retrieve_documents(user_query, top_k=3)
            
            if not retrieved_docs:
                logger.warning("No relevant documents found")
                return "I don't have information related to your question. Please contact our support team for assistance."
            
            # Step 2: Build context from retrieved documents
            logger.debug("Step 2: Building context")
            context = "\n\n".join([
                f"[Source: {doc['title']}]\n{doc['content']}"
                for doc in retrieved_docs
            ])
            
            # Step 3: Generate response with context grounding
            logger.debug("Step 3: Generating response")
            final_answer = self._generate_response(user_query, context)
            
            logger.info("Vector Pipeline: Query processed successfully")
            
            return final_answer
        
        except Exception as e:
            error_message = f"Vector Pipeline Error: {str(e)}"
            logger.error(error_message)
            return error_message
