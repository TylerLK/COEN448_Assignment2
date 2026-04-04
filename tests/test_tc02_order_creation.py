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

# Fixture to use an existing seeded user for order tests
@pytest.fixture(scope="module")
def test_user(mongo_client):
    users_db = mongo_client[os.getenv("DATABASE_NAME")]
    users_collection = users_db["users"]

    existing_user = users_collection.find_one({"userId": "u1"})
    assert existing_user is not None, "Expected existing seeded user u1 was not found"

    print("\nUsing existing seeded user for TC_02: u1")
    return existing_user

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
def test_tc02_order_integration(api_base_url, mongo_client, test_user, order_row):
    # 1. Prepare JSON payload
    user_emails = test_user['emails']
    
    payload = {
        "userId": test_user['userId'],
        "items": [
            {
                "itemId": order_row['itemId'],
                "quantity": int(order_row['quantity']),
                "price": float(order_row['price'])
            }
        ],
        "userEmails": user_emails,
        "orderStatus": order_row['orderStatus'],
        "deliveryAddress": test_user['deliveryAddress']
    }

    # 2. POST request to Order Service via API Gateway
    print(f"\nSending POST to /orders/ for user: {test_user['userId']} (Scenario: {order_row['itemId']})")
    response = requests.post(f"{api_base_url}/orders/", json=payload)
    
    # 3. Verify Response status
    assert response.status_code == 201, f"Failed to create order: {response.text}"
    created_order = response.json()
    order_id = created_order.get('orderId') # use orderid to validate the creation in the next steps
    assert order_id is not None, "orderId was not returned in the response"

    # 4. Retrieve matching orders through the API Gateway using the existing GET endpoint (trying to filter a bit using the orderstatus)
    print(f"Retrieving orders with GET /orders?status={order_row['orderStatus']}")
    get_response = requests.get(
        f"{api_base_url}/orders/",
        params={"status": order_row['orderStatus']}
    )

    # Once we get the response, we iterate through the list of orders and find the one with the matching orderId
    assert get_response.status_code == 200, f"Failed to retrieve orders: {get_response.text}"
    retrieved_orders = get_response.json()
    retrieved_order = next(
        (order for order in retrieved_orders if order.get('orderId') == order_id),
        None
    )

    # 5. Validate the retrieved order details
    # if there is none found that match the orderId, we fail the test
    assert retrieved_order is not None, \
        f"Order {order_id} was not found in GET /orders?status={order_row['orderStatus']}"
    assert retrieved_order['orderId'] == order_id
    assert retrieved_order['userId'] == test_user['userId'], \
        "Retrieved order does not reference the correct userId"
    assert retrieved_order['items'][0]['itemId'] == order_row['itemId']
    assert retrieved_order['items'][0]['quantity'] == int(order_row['quantity'])
    assert retrieved_order['items'][0]['price'] == float(order_row['price'])
    assert retrieved_order['orderStatus'] == order_row['orderStatus']
    assert retrieved_order['userEmails'] == user_emails
    assert retrieved_order['deliveryAddress'] == payload['deliveryAddress']

    # 6. Verify persisted state in MongoDB
    users_db = mongo_client[os.getenv("DATABASE_NAME")]
    orders_collection = users_db["orders"]
    
    db_order = orders_collection.find_one({"orderId": order_id})
    assert db_order is not None, f"Order with ID {order_id} not found in MongoDB"

    # 7. Assert persisted state integrity and user reference
    assert db_order['userId'] == test_user['userId'], "Order does not reference the correct userId"
    assert db_order['items'][0]['itemId'] == order_row['itemId']
    assert db_order['items'][0]['quantity'] == int(order_row['quantity'])
    assert db_order['items'][0]['price'] == float(order_row['price'])
    assert db_order['orderStatus'] == order_row['orderStatus']
    assert db_order['userEmails'] == user_emails
    assert db_order['deliveryAddress'] == payload['deliveryAddress']

    print(f"Successfully verified order {order_id} references user {test_user['userId']}")
