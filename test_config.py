"""
Configuration Test Script
Tests that your LLM provider is correctly configured.
Run this before starting the main chatbot.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file BEFORE importing Config
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import Config


def test_config():
    """Test configuration validity."""
    print("\n" + "=" * 60)
    print("HYBRID CHATBOT - Configuration Test")
    print("=" * 60 + "\n")
    
    try:
        # Test configuration
        print("[1/4] Validating configuration...")
        Config.validate()
        print("✓ Configuration is valid\n")
    except ValueError as e:
        print(f"✗ Configuration error: {e}\n")
        print("Please fix your .env file and try again.")
        return False
    except FileNotFoundError as e:
        print(f"✗ File error: {e}\n")
        print("Run: python scripts/init_db.py")
        return False
    
    # Display configuration
    print("[2/4] Current Configuration:")
    config_dict = Config.to_dict()
    for key, value in config_dict.items():
        if "key" in key.lower() or "secret" in key.lower():
            # Don't display secrets
            display_value = "***HIDDEN***"
        else:
            display_value = value
        print(f"  • {key}: {display_value}")
    print()
    
    # Test LLM client
    print("[3/4] Testing LLM Client Connection...")
    try:
        if Config.LLM_PROVIDER == "azure":
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=Config.AZURE_OPENAI_API_KEY,
                api_version=Config.AZURE_API_VERSION,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
            )
            print(f"✓ Azure OpenAI client initialized")
            print(f"  - Endpoint: {Config.AZURE_OPENAI_ENDPOINT}")
            print(f"  - Deployment: {Config.AZURE_OPENAI_DEPLOYMENT}")
            print(f"  - API Version: {Config.AZURE_API_VERSION}")
        else:
            import openai
            client = openai.Client(api_key=Config.OPENAI_API_KEY)
            print(f"✓ OpenAI client initialized")
            print(f"  - Model: {Config.OPENAI_MODEL}")
        
        print()
    except Exception as e:
        print(f"✗ Failed to initialize LLM client: {e}\n")
        if Config.LLM_PROVIDER == "azure":
            print("Azure Setup Help:")
            print("  1. Check AZURE_OPENAI_API_KEY is correct")
            print("  2. Check AZURE_OPENAI_ENDPOINT (should end with /)")
            print("  3. Check AZURE_OPENAI_DEPLOYMENT exists")
            print("  4. See AZURE_SETUP.md for detailed instructions")
        else:
            print("OpenAI Setup Help:")
            print("  1. Check OPENAI_API_KEY starts with 'sk-'")
            print("  2. Verify key at: https://platform.openai.com/api-keys")
            print("  3. Check for extra spaces in .env file")
        return False
    
    # Test database
    print("[4/4] Testing Database Connection...")
    try:
        import sqlite3
        with sqlite3.connect(Config.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM customers")
            customer_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders")
            order_count = cursor.fetchone()[0]
            print(f"✓ Database connection successful")
            print(f"  - Database: {Config.DB_PATH}")
            print(f"  - Customers: {customer_count}")
            print(f"  - Orders: {order_count}")
    except FileNotFoundError:
        print(f"✗ Database not found: {Config.DB_PATH}")
        print("  Run: python scripts/init_db.py")
        return False
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - Ready to run chatbot!")
    print("=" * 60)
    print("\nStart the chatbot with: python main.py\n")
    
    return True


if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
