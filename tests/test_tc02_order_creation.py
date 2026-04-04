import os
import csv
import pytest
import requests
import pymongo
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fixture to manage Docker Compose
@pytest.fixture(scope="module", autouse=True)
def docker_compose():
    # Start Docker Compose
    print("\nStarting Docker Compose...")
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.test.yml", "up", "--build", "-d"],
        check=True
    )
    
    # Wait for services to be ready
    wait_for_service("http://localhost:8001/")
    print("Docker Compose services are ready.")
    
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

# Fixture to create a temporary user for order tests
@pytest.fixture(scope="module")
def test_user_id(api_base_url):
    user_payload = {
        "firstName": "TC02",
        "lastName": "User",
        "emails": ["tc02.user@example.com"],
        "deliveryAddress": {
            "street": "Order Street",
            "city": "Order City",
            "state": "OS",
            "postalCode": "12345",
            "country": "Order Country"
        }
    }
    print(f"\nCreating test user for TC_02...")
    response = requests.post(f"{api_base_url}/users/", json=user_payload)
    assert response.status_code == 201
    user_id = response.json()['userId']
    print(f"Test user created with ID: {user_id}")
    return user_id

# Helper function to read tc02.csv
def load_csv_data():
    csv_file = os.path.join(os.path.dirname(__file__), "tc02.csv")
    datasets = []
    with open(csv_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            datasets.append(row)
    return datasets

# TC_02: Order Creation and User Reference
@pytest.mark.parametrize("order_row", load_csv_data())
def test_tc02_order_integration(api_base_url, mongo_client, test_user_id, order_row):
    # 1. Prepare JSON payload
    user_emails = [e.strip() for e in order_row['userEmails'].split(';') if e.strip()]
    
    payload = {
        "userId": test_user_id,
        "items": [
            {
                "itemId": order_row['itemId'],
                "quantity": int(order_row['quantity']),
                "price": float(order_row['price'])
            }
        ],
        "userEmails": user_emails,
        "orderStatus": order_row['orderStatus'],
        "deliveryAddress": {
            "street": order_row['street'],
            "city": order_row['city'],
            "state": order_row['state'],
            "postalCode": order_row['postalCode'],
            "country": order_row['country']
        }
    }

    # 2. POST request to Order Service via API Gateway
    print(f"\nSending POST to /orders/ for user: {test_user_id} (Scenario: {order_row['itemId']})")
    response = requests.post(f"{api_base_url}/orders/", json=payload)
    
    # 3. Verify Response status
    assert response.status_code == 201, f"Failed to create order: {response.text}"
    created_order = response.json()
    order_id = created_order.get('orderId')
    assert order_id is not None, "orderId was not returned in the response"

    # 4. Verify in MongoDB (Retrieval Simulation)
    users_db = mongo_client[os.getenv("DATABASE_NAME")]
    orders_collection = users_db["orders"]
    
    db_order = orders_collection.find_one({"orderId": order_id})
    assert db_order is not None, f"Order with ID {order_id} not found in MongoDB"

    # 5. Asset State Integrity and User Reference
    assert db_order['userId'] == test_user_id, "Order does not reference the correct userId"
    assert db_order['items'][0]['itemId'] == order_row['itemId']
    assert db_order['orderStatus'] == order_row['orderStatus']
    assert db_order['userEmails'] == user_emails

    print(f"Successfully verified order {order_id} references user {test_user_id}")
