"""
API Endpoint Tests for RAG Chatbot System

Tests for FastAPI endpoints: /api/query, /api/courses, /
Uses a separate test app to avoid static file mounting issues.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from models import SourceLink


# ============================================================================
# Test App Setup (avoids static file mounting issues)
# ============================================================================

def create_test_app(mock_rag_system):
    """Create a test FastAPI app with mocked RAGSystem"""
    app = FastAPI(title="Test RAG System")

    # Request/Response models (same as app.py)
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceLink]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "RAG Chatbot API", "status": "running"}

    return app


@pytest.fixture
def test_client(mock_rag_system):
    """Create test client with mocked RAGSystem"""
    app = create_test_app(mock_rag_system)
    return TestClient(app)


@pytest.fixture
def test_client_error(mock_rag_system_error):
    """Create test client with RAGSystem that raises errors"""
    app = create_test_app(mock_rag_system_error)
    return TestClient(app)


# ============================================================================
# POST /api/query Tests
# ============================================================================

@pytest.mark.api
class TestQueryEndpoint:
    """Tests for POST /api/query endpoint"""

    def test_query_without_session_id(self, test_client, mock_rag_system, sample_query_request):
        """Test query creates new session when session_id is not provided"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test_session_123"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_with_existing_session_id(self, test_client, mock_rag_system, sample_query_request_with_session):
        """Test query uses provided session_id"""
        response = test_client.post("/api/query", json=sample_query_request_with_session)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing_session_456"
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_query_returns_answer(self, test_client, sample_query_request):
        """Test query returns expected answer from RAGSystem"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "RAG stands for Retrieval-Augmented Generation."

    def test_query_returns_sources(self, test_client, sample_query_request):
        """Test query returns source citations"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 1
        assert data["sources"][0]["text"] == "Test Course - Lesson 0"
        assert data["sources"][0]["url"] == "https://example.com/lesson0"

    def test_query_calls_rag_system(self, test_client, mock_rag_system, sample_query_request):
        """Test query properly calls RAGSystem.query"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with("What is RAG?", "test_session_123")

    def test_query_missing_query_field(self, test_client):
        """Test query fails when query field is missing"""
        response = test_client.post("/api/query", json={})

        assert response.status_code == 422  # Validation error

    def test_query_empty_query_string(self, test_client):
        """Test query with empty string"""
        response = test_client.post("/api/query", json={"query": ""})

        # Should still be valid request (empty string is allowed by schema)
        assert response.status_code == 200

    def test_query_handles_rag_system_error(self, test_client_error):
        """Test query returns 500 when RAGSystem raises exception"""
        response = test_client_error.post("/api/query", json={"query": "test"})

        assert response.status_code == 500
        data = response.json()
        assert "RAG system query failed" in data["detail"]

    def test_query_with_long_query(self, test_client):
        """Test query handles long query strings"""
        long_query = "What is RAG and how does it work? " * 100
        response = test_client.post("/api/query", json={"query": long_query})

        assert response.status_code == 200

    def test_query_with_special_characters(self, test_client):
        """Test query handles special characters"""
        special_query = "What is 'RAG' & how does it <work>? @#$%^&*()"
        response = test_client.post("/api/query", json={"query": special_query})

        assert response.status_code == 200

    def test_query_response_structure(self, test_client, sample_query_request):
        """Test query response has correct structure"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields exist and have correct types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify source structure
        for source in data["sources"]:
            assert "text" in source
            assert "url" in source


# ============================================================================
# GET /api/courses Tests
# ============================================================================

@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint"""

    def test_get_courses_returns_stats(self, test_client, sample_course_stats):
        """Test courses endpoint returns course statistics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3

    def test_get_courses_titles_list(self, test_client):
        """Test courses endpoint returns correct course titles"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "Course A" in data["course_titles"]
        assert "Course B" in data["course_titles"]
        assert "Course C" in data["course_titles"]

    def test_get_courses_calls_analytics(self, test_client, mock_rag_system):
        """Test courses endpoint calls RAGSystem.get_course_analytics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_handles_error(self, test_client_error):
        """Test courses endpoint returns 500 on error"""
        response = test_client_error.get("/api/courses")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to get course analytics" in data["detail"]

    def test_get_courses_response_structure(self, test_client):
        """Test courses response has correct structure"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert all(isinstance(title, str) for title in data["course_titles"])


# ============================================================================
# GET / (Root) Tests
# ============================================================================

@pytest.mark.api
class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_returns_status(self, test_client):
        """Test root endpoint returns API status"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data

    def test_root_status_running(self, test_client):
        """Test root endpoint indicates API is running"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"


# ============================================================================
# Integration-style API Tests
# ============================================================================

@pytest.mark.api
class TestAPIIntegration:
    """Integration-style tests for API endpoints"""

    def test_multiple_queries_same_session(self, test_client, mock_rag_system):
        """Test multiple queries maintain same session"""
        # First query - creates session
        response1 = test_client.post("/api/query", json={"query": "First query"})
        session_id = response1.json()["session_id"]

        # Second query - uses same session
        response2 = test_client.post(
            "/api/query",
            json={"query": "Second query", "session_id": session_id}
        )

        assert response2.json()["session_id"] == session_id

    def test_query_after_getting_courses(self, test_client, mock_rag_system):
        """Test query works after fetching course list"""
        # Get courses first
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200

        # Then query
        query_response = test_client.post("/api/query", json={"query": "Test"})
        assert query_response.status_code == 200

    def test_invalid_json_body(self, test_client):
        """Test API handles invalid JSON gracefully"""
        response = test_client.post(
            "/api/query",
            content="invalid json{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_wrong_http_method_query(self, test_client):
        """Test query endpoint rejects GET requests"""
        response = test_client.get("/api/query")

        assert response.status_code == 405  # Method Not Allowed

    def test_wrong_http_method_courses(self, test_client):
        """Test courses endpoint rejects POST requests"""
        response = test_client.post("/api/courses", json={})

        assert response.status_code == 405


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.api
class TestAPIEdgeCases:
    """Edge cases and error handling for API endpoints"""

    def test_query_with_null_session_id(self, test_client, mock_rag_system):
        """Test query handles explicit null session_id"""
        response = test_client.post(
            "/api/query",
            json={"query": "test", "session_id": None}
        )

        assert response.status_code == 200
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_with_unicode(self, test_client):
        """Test query handles unicode characters"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is RAG? 日本語 emoji 🔥"}
        )

        assert response.status_code == 200

    def test_concurrent_requests_simulation(self, test_client):
        """Test simulating multiple rapid requests"""
        responses = []
        for i in range(5):
            response = test_client.post(
                "/api/query",
                json={"query": f"Query {i}"}
            )
            responses.append(response)

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

    def test_empty_sources_in_response(self, mock_rag_system):
        """Test query with empty sources list"""
        mock_rag_system.query.return_value = ("Answer with no sources", [])

        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.post("/api/query", json={"query": "test"})

        assert response.status_code == 200
        assert response.json()["sources"] == []

    def test_multiple_sources_in_response(self, mock_rag_system):
        """Test query with multiple sources"""
        mock_rag_system.query.return_value = (
            "Answer with multiple sources",
            [
                {"text": "Source 1", "url": "https://example.com/1"},
                {"text": "Source 2", "url": "https://example.com/2"},
                {"text": "Source 3", "url": "https://example.com/3"},
            ]
        )

        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.post("/api/query", json={"query": "test"})

        assert response.status_code == 200
        assert len(response.json()["sources"]) == 3
