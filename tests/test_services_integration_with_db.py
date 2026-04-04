import os
import csv
import pytest
import requests
import pymongo
import pika
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fixture to manage Docker Compose
@pytest.fixture(scope="module", autouse=True)
def docker_compose():
    # Start Docker Compose
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.test.yml", "up", "--build", "-d"],
        check=True
    )
    
    # Wait for services to be ready
    wait_for_service("http://localhost:8001/")
    
    yield  # Run tests
    
    # Tear down Docker Compose
    # subprocess.run(
    #     ["docker", "compose", "-f", "docker-compose.test.yml", "down", "-v"],
    #     check=True
    # )

# Helper function to wait for service readiness
def wait_for_service(url, timeout=200):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(url).status_code == 200:
                return
        except Exception:
            time.sleep(1)
    raise TimeoutError(f"Service at {url} not ready")


def restart_kong_with_weight(weight):
    env = os.environ.copy()
    env["P_VALUE"] = str(weight)

    subprocess.run(
        [
            "docker", "compose", "-f", "docker-compose.test.yml",
            "up", "-d", "--force-recreate", "kong"
        ],
        check=True,
        env=env
    )

    wait_for_service("http://localhost:8001/")

# Fixture for API base URL
@pytest.fixture(scope="module")
def api_base_url():
    return "http://localhost:8000"

# Fixture for MongoDB client
@pytest.fixture(scope="module")
def mongo_client():
    client = pymongo.MongoClient(
        host="localhost", 
        port=27017,
        username=os.getenv("MONGO_USERNAME"),
        password=os.getenv("MONGO_PASSWORD"),
        authSource="admin"
        )
    yield client
    client.close()

# Test: User Creation
def test_user_creation(api_base_url, mongo_client):
    # Create a new user
    user_payload = {
        "firstName": "Integration",
        "lastName": "Tester",
        "emails": ["integration.test@example.com"],
        "deliveryAddress": {
            "street": "123 Test Street",
            "city": "Testville",
            "state": "Test State",
            "postalCode": "12345",
            "country": "Test Country"
        }
    }
    
    # Send user creation request
    response = requests.post(
        f"{api_base_url}/users/", 
        json=user_payload
    )
    
    # Assertions
    assert response.status_code == 201
    created_user = response.json()
    assert created_user['firstName'] == "Integration"
    assert created_user['lastName'] == "Tester"
    
    # Verify user in MongoDB
    users_db = mongo_client[os.getenv("DATABASE_NAME")]
    users_collection = users_db["users"]
    user = users_collection.find_one({"userId": created_user["userId"]})
    assert user is not None
    assert user["emails"] == ["integration.test@example.com"]

# Test: User Update
def test_user_update(api_base_url, mongo_client):
    # First create a user
    user_payload = {
        "firstName": "Update",
        "lastName": "Tester",
        "emails": ["update.test@example.com"],
        "deliveryAddress": {
            "street": "123 Test Street",
            "city": "Testville",
            "state": "Test State",
            "postalCode": "12345",
            "country": "Test Country"
        }
    }
    
    # Create user
    create_response = requests.post(
        f"{api_base_url}/users/", 
        json=user_payload
    )
    
    assert create_response.status_code == 201
    created_user = create_response.json()
    user_id = created_user["userId"]
    
    # Update the user
    update_payload = {
        "emails": ["updated.email@example.com"],
        "deliveryAddress": {
            "street": "456 Update Street",
            "city": "Updateville",
            "state": "Update State",
            "postalCode": "54321",
            "country": "Update Country"
        }
    }
    
    # Send update request
    update_response = requests.put(
        f"{api_base_url}/users/{user_id}", 
        json=update_payload
    )
    
    # Assertions for the response
    assert update_response.status_code == 200
    update_result = update_response.json()
    
    # The response should contain both old and new user data
    old_user = update_result[0]
    new_user = update_result[1]
    
    # Check old user data
    assert old_user["emails"] == ["update.test@example.com"]
    assert old_user["deliveryAddress"]["street"] == "123 Test Street"
    
    # Check new user data
    assert new_user["emails"] == ["updated.email@example.com"]
    assert new_user["deliveryAddress"]["street"] == "456 Update Street"
    assert new_user["deliveryAddress"]["city"] == "Updateville"
    
    # Verify update in MongoDB
    users_db = mongo_client[os.getenv("DATABASE_NAME")]
    users_collection = users_db["users"]
    updated_user = users_collection.find_one({"userId": user_id})
    assert updated_user is not None
    assert updated_user["emails"] == ["updated.email@example.com"]
    assert updated_user["deliveryAddress"]["street"] == "456 Update Street"

# Additional Integration Testing Code
# Helper function to read tc01.csv
def load_csv_data():
    csv_file = os.path.join(os.path.dirname(__file__), "tc01.csv")
    datasets = []
    with open(csv_file, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            datasets.append(row)
    return datasets


def build_tc01_cases():
    cases = []
    for expected_version, route_weight in [("v1", 100), ("v2", 0)]:
        for index, user_data in enumerate(load_csv_data(), start=1):
            email_label = user_data["emails"].split(";")[0].strip()
            case_id = f"{expected_version}-row{index}-{email_label}"
            cases.append(
                pytest.param(route_weight, expected_version, user_data, id=case_id)
            )
    return cases


@pytest.fixture(scope="module")
def kong_route_manager():
    last_weight = {"value": None}

    def ensure_weight(weight):
        if last_weight["value"] != weight:
            restart_kong_with_weight(weight)
            last_weight["value"] = weight

    return ensure_weight


# Helper Function to run TC01 for a specific version
def run_tc01_for_version(api_base_url, mongo_client, user_data, expected_version):
    # 1. Prepare JSON payload
    emails = [e.strip() for e in user_data['emails'].split(';') if e.strip()]

    payload = {
        "emails": emails,
        "deliveryAddress": {
            "street": user_data['street'],
            "city": user_data['city'],
            "state": user_data['state'],
            "postalCode": user_data['postalCode'],
            "country": user_data['country']
        }
    }
    
    if user_data.get('firstName'): payload['firstName'] = user_data['firstName']
    if user_data.get('lastName'): payload['lastName'] = user_data['lastName']
    if user_data.get('phoneNumber'): payload['phoneNumber'] = user_data['phoneNumber']

    # 2. POST request to API Gateway
    print(f"\nSending POST to /users/ with emails: {emails}")
    response = requests.post(f"{api_base_url}/users/", json=payload)
    
    # 3. Verify Response status
    assert response.status_code == 201, f"Failed to create user: {response.text}"
    created_user = response.json()
    user_id = created_user.get('userId')
    assert user_id is not None, "userId was not returned in the response"

    # 4. Verify in MongoDB (Simulation of Retrieval)
    users_db = mongo_client[os.getenv("DATABASE_NAME")]
    users_collection = users_db["users"]
    
    # Search for the user in the database through mongo client
    db_user = users_collection.find_one({"userId": user_id})
    assert db_user is not None, f"User with ID {user_id} not found in MongoDB after creation"

    # 5. Assert State Integrity
    assert db_user['emails'] == emails
    assert db_user['deliveryAddress']['street'] == user_data['street']
    assert db_user['deliveryAddress']['city'] == user_data['city']
    
    if user_data.get('firstName'):
        assert db_user['firstName'] == user_data['firstName']
    if user_data.get('phoneNumber'):
        assert db_user['phoneNumber'] == user_data['phoneNumber']

    if expected_version == "v1":
        assert created_user.get("createdAt") is None, "v1 should not automatically set createdAt"
        assert created_user.get("updatedAt") is None, "v1 should not automatically set updatedAt"
        assert db_user.get("createdAt") is None, "v1 persisted unexpected createdAt"
        assert db_user.get("updatedAt") is None, "v1 persisted unexpected updatedAt"
    else:
        assert created_user.get("createdAt") is not None, "v2 should automatically set createdAt"
        assert created_user.get("updatedAt") is not None, "v2 should automatically set updatedAt"
        assert db_user.get("createdAt") is not None, "v2 did not persist createdAt"
        assert db_user.get("updatedAt") is not None, "v2 did not persist updatedAt"

    users_collection.delete_one({"userId": user_id})

    print(
        f"Successfully verified user creation for {emails} with userId: {user_id} "
        f"through {expected_version}"
    )


# TC_01
@pytest.mark.parametrize(
    "route_weight,expected_version,user_data",
    build_tc01_cases(),
)
def test_tc01_user_integration(api_base_url, mongo_client, kong_route_manager,
                               route_weight, expected_version, user_data):
    """
    This function tests each tc01.csv row as an explicit pytest case.
    The full v1 block runs first, Kong restarts once, then the full v2 block runs.
    """
    kong_route_manager(route_weight)
    run_tc01_for_version(api_base_url, mongo_client, user_data, expected_version)
