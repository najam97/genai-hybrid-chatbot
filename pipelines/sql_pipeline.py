"""
SQL Pipeline: Text-to-SQL generation, execution, and response formatting.
Implements read-only, injection-safe SQL query execution.
"""

import sqlite3
import openai
import logging
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)


class SQLPipeline:
    """
    Processes structured data queries by converting natural language to SQL,
    executing queries safely, and formatting results back to natural language.
    """
    
    # Database schema definition - used to guide LLM for SQL generation
    SCHEMA_DEFINITION = """
    Database Schema (SQLite):
    
    customers(id INTEGER PRIMARY KEY, name TEXT, email TEXT, country TEXT, signup_date DATE)
    - Stores customer information and registration details
    
    orders(id INTEGER PRIMARY KEY, customer_id INTEGER, product_name TEXT, amount REAL, order_date DATE)
    - Tracks customer orders with amounts and dates
    - Foreign key: customer_id references customers(id)
    
    products(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL, stock_quantity INTEGER)
    - Catalog of available products with pricing and inventory
    """
    
    # SQL keywords that indicate non-SELECT (unsafe) operations
    UNSAFE_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "EXEC", "EXECUTE"}
    
    def __init__(self, db_path: str, client: openai.Client, model: str = "gpt-4o"):
        """
        Initialize the SQL Pipeline.
        
        Args:
            db_path: Path to SQLite database file
            client: OpenAI API client instance
            model: Model to use for SQL generation (default: gpt-4o)
        """
        self.db_path = db_path
        self.client = client
        self.model = model
        self.max_tokens_sql = 500
    
    def _is_safe_query(self, query: str) -> bool:
        """
        Validate that a SQL query is read-only (SELECT only).
        
        Args:
            query: SQL query string
            
        Returns:
            bool: True if query is safe (SELECT only), False otherwise
        """
        # Remove comments and normalize whitespace
        query_cleaned = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
        query_cleaned = re.sub(r'/\*.*?\*/', '', query_cleaned, flags=re.DOTALL)
        query_upper = query_cleaned.upper().strip()
        
        # Check for unsafe keywords
        for keyword in self.UNSAFE_KEYWORDS:
            if keyword in query_upper:
                logger.warning(f"Unsafe SQL keyword detected: {keyword}")
                return False
        
        # Ensure query starts with SELECT
        if not query_upper.startswith("SELECT"):
            logger.warning(f"Non-SELECT query detected: {query_upper[:50]}")
            return False
        
        return True
    
    def execute_read_only_query(self, query: str) -> str:
        """
        Execute a SQL query in read-only mode with safety checks.
        
        Args:
            query: SQL query to execute
            
        Returns:
            str: JSON-serialized results from the query
            
        Raises:
            ValueError: If query contains unsafe keywords or non-SELECT operations
        """
        # Security: Prevent injection and non-read operations
        if not self._is_safe_query(query):
            raise ValueError(
                "Only SELECT queries are permitted. "
                "Query must not contain DROP, DELETE, UPDATE, INSERT, or other DML operations."
            )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()
                
                # Execute query with timeout
                cursor.execute(query)
                results = cursor.fetchall()
                
                # Get column names
                column_names = [description[0] for description in cursor.description] if cursor.description else []
                
                # Convert to list of dictionaries
                result_list = [dict(zip(column_names, row)) for row in results]
                
                logger.info(f"Query executed successfully. Returned {len(result_list)} rows.")
                
                return str(result_list)
        
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise ValueError(f"Database error: {str(e)}")
    
    def _generate_sql_query(self, user_query: str) -> str:
        """
        Generate SQL query from natural language using LLM.
        
        Args:
            user_query: Natural language question from user
            
        Returns:
            str: Generated SQL query
        """
        prompt = f"""
You are an expert SQL query generator. Your job is to convert natural language questions into precise SQLite SQL queries.

Database Schema:
{self.SCHEMA_DEFINITION}

CRITICAL RULES:
1. Generate ONLY SELECT queries - never use INSERT, UPDATE, DELETE, or DROP
2. Use appropriate JOIN operations when needed to relate tables
3. Handle aggregations (COUNT, SUM, AVG, MAX, MIN) when asking for metrics
4. Use WHERE clauses for filtering based on conditions
5. Use ORDER BY and LIMIT for sorting and limiting results
6. Use DATE functions for date-based queries
7. Always use proper table aliases for clarity in joins

User Question: {user_query}

Generate ONLY the raw SQL query. No markdown, no explanations, no code blocks.
Return the pure SQL statement ready to execute.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=self.max_tokens_sql
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Clean up markdown formatting if present
            sql_query = sql_query.strip("```").strip("sql").strip()
            
            logger.debug(f"Generated SQL: {sql_query}")
            
            return sql_query
        
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise ValueError(f"SQL generation error: {str(e)}")
    
    def _format_response(self, user_query: str, raw_data: str) -> str:
        """
        Format raw database results into a natural language response.
        
        Args:
            user_query: Original user question
            raw_data: Raw query results (JSON string)
            
        Returns:
            str: Natural language response
        """
        prompt = f"""
You are a helpful data analyst. A user asked a question and we retrieved data from a database.
Your job is to provide a clear, concise, natural language summary of the data.

User Question: {user_query}

Raw Database Results: {raw_data}

Provide a clear answer based on the data. If the data is empty, explain that no results were found.
Keep the response concise but informative.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Response formatting failed: {e}")
            return f"Error formatting response: {str(e)}"
    
    def run(self, user_query: str) -> str:
        """
        Execute the SQL pipeline end-to-end.
        
        Args:
            user_query: Natural language question about structured data
            
        Returns:
            str: Natural language response with query results
        """
        logger.info(f"SQL Pipeline: Processing query: {user_query}")
        
        try:
            # Step 1: Generate SQL query
            logger.debug("Step 1: Generating SQL query")
            sql_query = self._generate_sql_query(user_query)
            
            # Step 2: Execute query safely
            logger.debug("Step 2: Executing query")
            raw_data = self.execute_read_only_query(sql_query)
            
            # Step 3: Format response
            logger.debug("Step 3: Formatting response")
            final_answer = self._format_response(user_query, raw_data)
            
            logger.info("SQL Pipeline: Query processed successfully")
            
            return final_answer
        
        except Exception as e:
            error_message = f"SQL Pipeline Error: {str(e)}"
            logger.error(error_message)
            return error_message
