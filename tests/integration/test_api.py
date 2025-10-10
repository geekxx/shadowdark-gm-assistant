#!/usr/bin/env python3

"""
Test script for the FastAPI endpoints
"""

import sys
import os
import requests
import json

API_BASE = "http://127.0.0.1:8000"

def test_summarize_endpoint():
    """Test the enhanced summarize endpoint"""
    print("Testing /sessions/summarize endpoint...")
    
    payload = {
        "text": "GM: You enter the cursed library. Kira: I cast Light. GM: Three shadow rats attack! Thane: I fight them with my sword!",
        "campaign_id": 1,
        "use_rag": True,
        "save_to_db": True
    }
    
    try:
        response = requests.post(f"{API_BASE}/sessions/summarize", json=payload)
        response.raise_for_status()
        
        result = response.json()
        print("✅ Summarize endpoint working!")
        print(f"Generated notes preview: {result['notes'][:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Error testing summarize endpoint: {e}")
        return False

def test_sessions_list():
    """Test the sessions list endpoint"""
    print("\nTesting /sessions endpoint...")
    
    try:
        response = requests.get(f"{API_BASE}/sessions")
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Sessions list endpoint working! Found {len(result['sessions'])} sessions")
        
        if result['sessions']:
            session_id = result['sessions'][0]['id']
            return test_session_notes(session_id)
        else:
            print("No sessions found to test notes endpoint")
            return True
            
    except Exception as e:
        print(f"❌ Error testing sessions list endpoint: {e}")
        return False

def test_session_notes(session_id):
    """Test the session notes endpoint"""
    print(f"\nTesting /sessions/{session_id}/notes endpoint...")
    
    try:
        response = requests.get(f"{API_BASE}/sessions/{session_id}/notes")
        response.raise_for_status()
        
        result = response.json()
        print("✅ Session notes endpoint working!")
        print(f"Session {session_id} from {result['date']}")
        print(f"Notes preview: {result['notes'][:100] if result['notes'] else 'No notes'}...")
        return True
        
    except Exception as e:
        print(f"❌ Error testing session notes endpoint: {e}")
        return False

def test_rag_endpoints():
    """Test RAG endpoints"""
    print("\nTesting RAG endpoints...")
    
    # Test ingest
    ingest_payload = {
        "text": "# Test Rule\n\nThis is a test rule for combat.",
        "title": "Test Rule",
        "doctype": "rule"
    }
    
    try:
        response = requests.post(f"{API_BASE}/rag/ingest", json=ingest_payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ RAG ingest working! Document ID: {result['document_id']}")
        
        # Test query
        query_payload = {
            "query": "combat rules",
            "k": 3
        }
        
        response = requests.post(f"{API_BASE}/rag/query", json=query_payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ RAG query working! Found {len(result['results'])} results")
        return True
        
    except Exception as e:
        print(f"❌ Error testing RAG endpoints: {e}")
        return False

def main():
    print("Testing Shadowdark GM API endpoints...")
    print("=" * 50)
    
    # Test health endpoint first
    try:
        response = requests.get(f"{API_BASE}/health")
        response.raise_for_status()
        print("✅ Health endpoint working!")
    except Exception as e:
        print(f"❌ API server not responding: {e}")
        print("Make sure the server is running with: uvicorn apps.api.main:app --reload")
        return
    
    # Run all tests
    tests = [
        test_summarize_endpoint,
        test_sessions_list,
        test_rag_endpoints
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"API Tests: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All API endpoints working correctly!")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()