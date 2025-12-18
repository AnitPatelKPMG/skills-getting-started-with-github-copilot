"""
Test cases for the High School Management System API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Save original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Test cases for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test cases for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check that Chess Club exists (from initial data)
        assert "Chess Club" in data
        assert "description" in data["Chess Club"]
        assert "schedule" in data["Chess Club"]
        assert "max_participants" in data["Chess Club"]
        assert "participants" in data["Chess Club"]
    
    def test_get_activities_has_correct_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_name, str)
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)


class TestSignupForActivity:
    """Test cases for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_valid_activity(self, client):
        """Test successful signup for an activity"""
        test_email = "newstudent@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": test_email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert test_email in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert test_email in activities_data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/NonExistent Club/signup",
            params={"email": "test@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_email(self, client):
        """Test that duplicate signups are rejected"""
        test_email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": test_email}
        )
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": test_email}
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_when_activity_full(self, client):
        """Test signup rejection when activity is at capacity"""
        # Set activity to have only 1 spot left
        activities["Chess Club"]["participants"] = ["student" + str(i) + "@mergington.edu" 
                                                     for i in range(activities["Chess Club"]["max_participants"])]
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "toolate@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "full" in data["detail"].lower()
    
    def test_signup_with_url_encoded_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        test_email = "urltest@mergington.edu"
        # "Chess Club" URL encoded
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": test_email}
        )
        
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Test cases for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client):
        """Test successful unregistration of a participant"""
        # First, sign up a student
        test_email = "tounregister@mergington.edu"
        signup_response = client.post(
            "/activities/Chess Club/signup",
            params={"email": test_email}
        )
        assert signup_response.status_code == 200
        
        # Now unregister
        unregister_response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": test_email}
        )
        
        assert unregister_response.status_code == 200
        data = unregister_response.json()
        assert "message" in data
        assert test_email in data["message"]
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert test_email not in activities_data["Chess Club"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistration from an activity that doesn't exist"""
        response = client.delete(
            "/activities/NonExistent Club/unregister",
            params={"email": "test@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_non_participant(self, client):
        """Test unregistration of someone not registered"""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_with_url_encoded_activity_name(self, client):
        """Test unregister with URL-encoded activity name"""
        test_email = "urltest2@mergington.edu"
        
        # Sign up first
        client.post(
            "/activities/Chess Club/signup",
            params={"email": test_email}
        )
        
        # Unregister with URL encoding
        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": test_email}
        )
        
        assert response.status_code == 200


class TestIntegrationScenarios:
    """Integration tests for complete user workflows"""
    
    def test_complete_signup_and_unregister_flow(self, client):
        """Test a complete flow: signup -> verify -> unregister -> verify"""
        test_email = "integration@mergington.edu"
        activity_name = "Drama Club"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity_name]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": test_email}
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities")
        assert len(after_signup.json()[activity_name]["participants"]) == initial_count + 1
        assert test_email in after_signup.json()[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": test_email}
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        after_unregister = client.get("/activities")
        assert len(after_unregister.json()[activity_name]["participants"]) == initial_count
        assert test_email not in after_unregister.json()[activity_name]["participants"]
    
    def test_multiple_students_signup(self, client):
        """Test multiple students can sign up for the same activity"""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in students:
            response = client.post(
                "/activities/Science Club/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all students are registered
        activities_response = client.get("/activities")
        participants = activities_response.json()["Science Club"]["participants"]
        
        for email in students:
            assert email in participants
