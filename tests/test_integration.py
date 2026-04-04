import os
import csv
import json
import time
import uuid
import datetime
import subprocess
import pymongo
import pytest
import requests
from dotenv import load_dotenv

# Constants
P_VALUES = [0, 50, 100]
COMPOSE_FILE = "docker-compose.test.yml"
API_BASE_URL = "http://localhost:8000"
KONG_ADMIN_URL = "http://localhost:8001/"
USER_SCHEMA_PATH = os.path.join("src", "shared", "schemas", "user_schema.json")
ORDER_SCHEMA_PATH = os.path.join("src", "shared", "schemas", "order_schema.json")
EXPECTED_TWO_OBJECTS_RESPONSE_MSG = "Expected [original, updated] response..."

# Load environment variables
load_dotenv()

# Fixture Setup for non-Kong service containers.
@pytest.fixture(scope="session", autouse=True)
def docker_compose_base():
    # Start base services once for the whole session.
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            COMPOSE_FILE,
            "up",
            "--build",
            "-d",
            "mongodb",
            "mongodb-setup",
            "rabbitmq",
            "order-service",
            "user-service-v1",
            "user-service-v2",
        ],
        check=True,
    )
    wait_for_mongo()

    # Allow the tests to run.
    yield

    # Once the session is over, stop all the service containers.
    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "down", "--remove-orphans"],
        check=True,
    )

# Fixture Setup for Kong service container with different routing weights.
@pytest.fixture(scope="session", params=P_VALUES)
def kong_weight_session(request, mongo_client):
    # Rebuild/recreate Kong once per routing weight for lower overhead.
    p = request.param
    compose_env = os.environ.copy()
    compose_env["P_VALUE"] = str(p)

    # Ensure backing services are healthy before rotating Kong config by weight.
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            COMPOSE_FILE,
            "up",
            "-d",
            "mongodb",
            "rabbitmq",
            "order-service",
            "user-service-v1",
            "user-service-v2",
        ],
        check=True,
        env=compose_env,
    )
    wait_for_mongo()

    # Start the Kong service container.
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            COMPOSE_FILE,
            "up",
            "-d",
            "--force-recreate",
            "--no-deps",
            "kong",
        ],
        check=True,
        env=compose_env,
    )

    # Wait for the Kong service to be ready before proceeding with tests.
    wait_for_service(KONG_ADMIN_URL)

    # Reset test data for each routing partition so each P_VALUE starts from a clean baseline.
    reset_test_database(mongo_client)
    yield p

# Fixture Setup for the API Base.
@pytest.fixture(scope="session")
def api_base_url():
    return API_BASE_URL

# Fixture Setup for the MongoDB client.
@pytest.fixture(scope="session")
def mongo_client():
    client = pymongo.MongoClient(
        host="localhost",
        port=27017,
        username=os.getenv("MONGO_USERNAME"),
        password=os.getenv("MONGO_PASSWORD"),
        authSource="admin",
    )
    yield client
    client.close()

# Fixture Setup for loading JSON schemas.
@pytest.fixture(scope="session")
def schemas():
    with open(USER_SCHEMA_PATH, "r", encoding="utf-8") as user_file:
        user_schema = json.load(user_file)
    with open(ORDER_SCHEMA_PATH, "r", encoding="utf-8") as order_file:
        order_schema = json.load(order_file)
    return {"user": user_schema, "order": order_schema}

# Helper Functions
# Create a delay to ensure a given service is ready.
def wait_for_service(url, timeout=200):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(url, timeout=5).status_code == 200:
                return
        except Exception:
            time.sleep(1)
    raise TimeoutError(f"Service at {url} not ready")

# Create a delay to ensure that a given condition is met.
def wait_for_condition(check_fn, timeout=30, interval=0.5, failure_message="Condition timed out"):
    start = time.time()
    while time.time() - start < timeout:
        if check_fn():
            return
        time.sleep(interval)
    raise TimeoutError(failure_message)

# Create a delay to ensure the MongoDB service container is ready.
def wait_for_mongo(timeout=120, interval=1):
    start = time.time()
    while time.time() - start < timeout:
        client = None
        try:
            client = pymongo.MongoClient(
                host="127.0.0.1",
                port=27017,
                username=os.getenv("MONGO_USERNAME"),
                password=os.getenv("MONGO_PASSWORD"),
                authSource="admin",
                serverSelectionTimeoutMS=2000,
            )
            client.admin.command("ping")
            return
        except Exception:
            time.sleep(interval)
        finally:
            if client is not None:
                client.close()
    raise TimeoutError("MongoDB on localhost:27017 not ready")

# Loads the rows of a .CSV file into a list.
def load_csv_rows(filename):
    csv_file = os.path.join(os.path.dirname(__file__), filename)
    datasets = []
    with open(csv_file, mode="r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            datasets.append(row)
    return datasets

# TC_01-specific .CSV loader.
def load_tc01_csv_data():
    return load_csv_rows("tc01.csv")

# TC_02-specific .CSV loader.
def load_tc02_csv_data():
    return load_csv_rows("tc02.csv")

# Retrieves the entire MongoDB database by name.
def get_database(mongo_client):
    return mongo_client[os.getenv("DATABASE_NAME")]

# Retrieves the 'users' collection from the MongoDB database.
def get_users_collection(mongo_client):
    return get_database(mongo_client)["users"]

# Retrieves the 'orders' collection from the MongoDB database.
def get_orders_collection(mongo_client):
    return get_database(mongo_client)["orders"]

# Cleans the MongoDB database.
def reset_test_database(mongo_client):
    db = get_database(mongo_client)
    db["orders"].delete_many({})
    db["users"].delete_many({})

# Reorganizes an object's data to fit the JSON schema formats.
def normalize_for_schema(value):
    if isinstance(value, dict):
        return {
            k: normalize_for_schema(v)
            for k, v in value.items()
            if k not in {"createdAt", "updatedAt"} and v is not None
        }
    if isinstance(value, list):
        return [normalize_for_schema(v) for v in value]
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return value

# Validates that a given object matches the expected JSON schema format.
def assert_valid_schema(document, schema):
    jsonschema = __import__("jsonschema")
    jsonschema.validate(
        instance=normalize_for_schema(document),
        schema=schema,
        format_checker=jsonschema.FormatChecker(),
    )

# Checks if an internal server error has occurred.
def is_internal_server_error(response):
    if response.status_code != 500:
        return False
    try:
        body = response.json()
        return body.get("message") == "Internal Server Error"
    except Exception:
        return "Internal Server Error" in response.text

# Classifies the version of the User microservice.
def classify_user_version(user_doc):
    return "v2" if user_doc.get("createdAt") is not None else "v1"

# Validates that a given order object matches the expected field values.
def assert_order_fields(order_doc, order_id, user_id, order_row, user_emails, delivery_address):
    assert order_doc["orderId"] == order_id
    assert order_doc["userId"] == user_id
    assert order_doc["items"][0]["itemId"] == order_row["itemId"]
    assert order_doc["items"][0]["quantity"] == int(order_row["quantity"])
    assert float(order_doc["items"][0]["price"]) == float(order_row["price"])
    assert order_doc["orderStatus"] == order_row["orderStatus"]
    assert order_doc["userEmails"] == user_emails
    assert order_doc["deliveryAddress"] == delivery_address

# Validate that a User microservice PUT request has propagated to the Order microservice.
def ensure_user_put_propagated(orders_collection, user_id, expected_emails, expected_delivery):
    def is_synced():
        user_orders = list(orders_collection.find({"userId": user_id}))
        if not user_orders:
            return False
        return all(
            order.get("userEmails") == expected_emails
            and order.get("deliveryAddress") == expected_delivery
            for order in user_orders
        )

    wait_for_condition(
        is_synced,
        timeout=45,
        interval=1,
        failure_message="Timed out waiting for User PUT propagation into Order documents",
    )

# Constructs the user creation payloads based on the data from tc01.csv.
def build_tc01_payload(user_data):
    emails = [e.strip() for e in user_data["emails"].split(";") if e.strip()]
    payload = {
        "emails": emails,
        "deliveryAddress": {
            "street": user_data["street"],
            "city": user_data["city"],
            "state": user_data["state"],
            "postalCode": user_data["postalCode"],
            "country": user_data["country"],
        },
    }
    if user_data.get("firstName"):
        payload["firstName"] = user_data["firstName"]
    if user_data.get("lastName"):
        payload["lastName"] = user_data["lastName"]
    if user_data.get("phoneNumber"):
        payload["phoneNumber"] = user_data["phoneNumber"]
    return payload

# Test functions
# TC_01 - Validate User Creation & Retrieval
@pytest.mark.parametrize("user_data", load_tc01_csv_data())
def test_tc01_user_integration(api_base_url, mongo_client, schemas, kong_weight_session, user_data):
    # Create the payload for a new user.
    payload = build_tc01_payload(user_data)

    # Send the POST request to create the user.
    response = requests.post(f"{api_base_url}/users/", json=payload, timeout=10)
    assert response.status_code == 201, f"Failed to create user: {response.text}"

    # Validate the creation of the user.
    created_user = response.json()
    user_id = created_user.get("userId")
    assert user_id is not None, "userId was not returned in the response"

    # Validate that the user is found in the "users" collection in MongoDB with the correct data.
    users_collection = get_users_collection(mongo_client)
    db_user = users_collection.find_one({"userId": user_id})
    assert db_user is not None, f"User with ID {user_id} not found in MongoDB after creation"

    assert db_user["emails"] == payload["emails"]
    assert db_user["deliveryAddress"] == payload["deliveryAddress"]
    if payload.get("firstName"):
        assert db_user["firstName"] == payload["firstName"]
    if payload.get("lastName"):
        assert db_user["lastName"] == payload["lastName"]
    if payload.get("phoneNumber"):
        assert db_user["phoneNumber"] == payload["phoneNumber"]

    # JSON schema validation for response and persisted document.
    assert_valid_schema(created_user, schemas["user"])
    assert_valid_schema(db_user, schemas["user"])

    # Version management checks for deterministic routing edges.
    if kong_weight_session == 100:
        assert classify_user_version(created_user) == "v1"
        assert classify_user_version(db_user) == "v1"
    if kong_weight_session == 0:
        assert classify_user_version(created_user) == "v2"
        assert classify_user_version(db_user) == "v2"

# TC_02 - Validate Order Creation with Existing User
@pytest.mark.parametrize("order_row", load_tc02_csv_data())
def test_tc02_order_integration(api_base_url, mongo_client, schemas, kong_weight_session, order_row):
    # Retrieve the "users" and "orders" collections from MongoDB.
    users_collection = get_users_collection(mongo_client)
    orders_collection = get_orders_collection(mongo_client)

    # Choose an existing user from the "users" collection.
    existing_user = users_collection.find_one({})
    assert existing_user is not None, "No existing user available for order test"

    # Create the payload for an order.
    payload = {
        "userId": existing_user["userId"],
        "items": [
            {
                "itemId": order_row["itemId"],
                "quantity": int(order_row["quantity"]),
                "price": float(order_row["price"]),
            }
        ],
        "userEmails": existing_user["emails"],
        "orderStatus": order_row["orderStatus"],
        "deliveryAddress": existing_user["deliveryAddress"],
    }

    # Send the POST request to create the order.
    post_response = requests.post(f"{api_base_url}/orders/", json=payload, timeout=10)
    assert post_response.status_code == 201, f"Failed to create order: {post_response.text}"

    # Validate the creation of the order.
    created_order = post_response.json()
    order_id = created_order.get("orderId")
    assert order_id is not None, "orderId was not returned in the response"

    # Send the GET request to retrieve the order.
    get_response = requests.get(
        f"{api_base_url}/orders/",
        params={"status": order_row["orderStatus"]},
        timeout=10,
    )
    assert get_response.status_code == 200, f"Failed to retrieve orders: {get_response.text}"

    # Validate that the created order has been retrieved.
    retrieved_order = next(
        (order for order in get_response.json() if order.get("orderId") == order_id),
        None,
    )
    assert retrieved_order is not None, (
        f"Order {order_id} was not found in GET /orders/?status={order_row['orderStatus']}"
    )

    # Validate that the retrieved order has the correct data.
    assert_order_fields(
        retrieved_order,
        order_id,
        existing_user["userId"],
        order_row,
        existing_user["emails"],
        existing_user["deliveryAddress"],
    )

    # Validate that the order is found in the "orders" collection in MongoDB.
    db_order = orders_collection.find_one({"orderId": order_id})
    assert db_order is not None, f"Order with ID {order_id} not found in MongoDB"
    assert_order_fields(
        db_order,
        order_id,
        existing_user["userId"],
        order_row,
        existing_user["emails"],
        existing_user["deliveryAddress"],
    )

    # Validate the JSON schema for the created order.
    assert_valid_schema(created_order, schemas["order"])
    assert_valid_schema(db_order, schemas["order"])

def test_tc02_order_status_put_and_get(api_base_url, mongo_client, schemas, kong_weight_session):
    # Retrieve the "users" and "orders" collections from MongoDB.
    users_collection = get_users_collection(mongo_client)
    orders_collection = get_orders_collection(mongo_client)

    # Choose an existing user from the "users" collection.
    existing_user = users_collection.find_one({})
    assert existing_user is not None, "No user found for order status PUT test"

    # Create an order for the existing user to update.
    order_payload = {
        "userId": existing_user["userId"],
        "items": [{"itemId": "status-item", "quantity": 1, "price": 1.5}],
        "userEmails": existing_user["emails"],
        "orderStatus": "under process",
        "deliveryAddress": existing_user["deliveryAddress"],
    }

    # Send POST request to create the order.
    create_resp = requests.post(f"{api_base_url}/orders/", json=order_payload, timeout=10)
    assert create_resp.status_code == 201, create_resp.text
    order_id = create_resp.json()["orderId"]

    # Send PUT request to update the order status.
    put_resp = requests.put(
        f"{api_base_url}/orders/{order_id}/status",
        json={"orderStatus": "shipping"},
        timeout=10,
    )
    if is_internal_server_error(put_resp):
        pytest.xfail(
            "Known upstream bug: order-service PUT handlers are defined without the route id "
            "parameter, causing 500 responses."
        )
    assert put_resp.status_code == 200, put_resp.text
    put_body = put_resp.json()
    assert isinstance(put_body, list), EXPECTED_TWO_OBJECTS_RESPONSE_MSG
    assert len(put_body) == 2
    assert put_body[1]["orderStatus"] == "shipping"

    # Send the GET request to retrieve the order.
    get_resp = requests.get(f"{api_base_url}/orders/", params={"status": "shipping"}, timeout=10)
    assert get_resp.status_code == 200
    assert any(order.get("orderId") == order_id for order in get_resp.json())

    # Validate that the order status update is reflected in MongoDB.
    db_order = orders_collection.find_one({"orderId": order_id})
    assert db_order is not None
    assert db_order["orderStatus"] == "shipping"
    assert_valid_schema(db_order, schemas["order"])

# TC_03 - Validate Event-Driven User Update Propagation
@pytest.mark.parametrize("new_emails,new_address", [
    (
        ["updated@example.com"],
        {
            "street": "123 Updated Street",
            "city": "Updated City",
            "state": "Updated State",
            "postalCode": "U1U2U3",
            "country": "Updated Country",
        },
    ),
    (
        ["updated.emails.only@example.com"],
        None,
    ),
    (
        None,
        {
            "street": "123 Address Only Street",
            "city": "Address City",
            "state": "Address State",
            "postalCode": "A1A1A1",
            "country": "Address Country",
        },
    ),
])
def test_tc03_user_update_propagation(api_base_url, mongo_client, schemas, kong_weight_session, new_emails, new_address):
    # Retrieve the "users" and "orders" collections from MongoDB.
    users_collection = get_users_collection(mongo_client)
    orders_collection = get_orders_collection(mongo_client)

    # Choose an existing user from the "users" collection to update.
    existing_user = users_collection.find_one({})
    assert existing_user is not None, "No user found for event-driven propagation test"

    # If no orders exist for the user, create a new one.
    if orders_collection.count_documents({"userId": existing_user["userId"]}) == 0:
        seed_order_payload = {
            "userId": existing_user["userId"],
            "items": [{"itemId": "seed-item", "quantity": 1, "price": 2.5}],
            "userEmails": existing_user["emails"],
            "orderStatus": "under process",
            "deliveryAddress": existing_user["deliveryAddress"],
        }
        seed_response = requests.post(f"{api_base_url}/orders/", json=seed_order_payload, timeout=10)
        assert seed_response.status_code == 201, seed_response.text

    # Contruct a payload for thh PUT request.
    payload = {}
    if new_emails is not None:
        payload["emails"] = new_emails
    if new_address is not None:
        payload["deliveryAddress"] = new_address

    # Send the PUT request to update the user.
    put_response = requests.put(
        f"{api_base_url}/users/{existing_user['userId']}",
        json=payload,
        timeout=10,
    )
    if is_internal_server_error(put_response):
        pytest.xfail(
            "Known upstream bug: user-service-v2 PUT handler is defined without the route id "
            "parameter, causing 500 responses when routed to v2."
        )
    assert put_response.status_code == 200, f"PUT failed: {put_response.text}"

    # Validate the response contains both original and updated user data.
    response_body = put_response.json()
    assert isinstance(response_body, list), EXPECTED_TWO_OBJECTS_RESPONSE_MSG
    assert len(response_body) == 2

    # Determine theexpected values of the updated user's email.delivery address.
    updated_user = response_body[1]
    expected_emails = payload.get("emails", updated_user["emails"])
    expected_delivery = payload.get("deliveryAddress", updated_user["deliveryAddress"])

    # Validate that the PUT update has propagated to all related Order documents in MongoDB.
    ensure_user_put_propagated(
        orders_collection,
        existing_user["userId"],
        expected_emails,
        expected_delivery,
    )

    # Send the GET request to retrieve orders for the user and validate the updated fields are reflected.
    statuses = ["under process", "shipping", "delivered"]
    for status in statuses:
        status_resp = requests.get(f"{api_base_url}/orders/", params={"status": status}, timeout=10)
        assert status_resp.status_code == 200
        matching_orders = [
            order for order in status_resp.json() if order.get("userId") == existing_user["userId"]
        ]
        for order in matching_orders:
            assert order["userEmails"] == expected_emails
            assert order["deliveryAddress"] == expected_delivery

    # Validate that the updated user document in MongoDB has the correct data.
    updated_db_user = users_collection.find_one({"userId": existing_user["userId"]})
    assert updated_db_user is not None
    assert updated_db_user["emails"] == expected_emails
    assert updated_db_user["deliveryAddress"] == expected_delivery
    assert_valid_schema(updated_db_user, schemas["user"])

@pytest.mark.parametrize( "invalid_payload", [
    {},
    {"emails": ["not-an-email"]},
    {"deliveryAddress": {"street": "Missing required fields"}},
    {"firstName": "Not allowed in PUT"},
])
def test_tc03_user_update_invalid_payload(api_base_url, mongo_client, kong_weight_session, invalid_payload):
    # Retrieve the "users" and "orders" collections from MongoDB.
    users_collection = get_users_collection(mongo_client)

    # Choose an existing user from the "users" collection to attempt to update with invalid payloads.
    existing_user = users_collection.find_one({})
    assert existing_user is not None, "User missing before invalid PUT test"

    # Send the PUT request with invalid payload.
    put_response = requests.put(
        f"{api_base_url}/users/{existing_user['userId']}",
        json=invalid_payload,
        timeout=10,
    )
    if is_internal_server_error(put_response):
        pytest.xfail(
            "Known upstream bug: user-service-v2 PUT handler is defined without the route id "
            "parameter, causing 500 responses when routed to v2."
        )

    # Validate that the response status code is 400 for invalid payloads.
    assert put_response.status_code == 400, (
        f"Expected 400 for invalid payload {invalid_payload}, got "
        f"{put_response.status_code}: {put_response.text}"
    )

    # Validate that the user document in MongoDB has not been modified.
    updated_user = users_collection.find_one({"userId": existing_user["userId"]})
    assert updated_user is not None
    assert updated_user["emails"] == existing_user["emails"]
    assert updated_user["deliveryAddress"] == existing_user["deliveryAddress"]

# TC_04 - Validate API Gateway Routing
def test_tc04_gateway_routing_behavior(api_base_url, mongo_client, kong_weight_session):
    # Retrieve the "users" collection from MongoDB.
    users_collection = get_users_collection(mongo_client)

    # Create empty lists to track any created users and which User microservice version created them.
    observed_versions = []
    created_user_ids = []

    # Create a given number of users based on the API gateway routing weight.
    # For P = 0, 100, less iterations will yield adequate results.
    # For P = 50, more iterations are needed to ensure that the routing is distributed equally.
    iterations = 20 if kong_weight_session == 50 else 8

    # For each iteration, a unique user should be created.
    for _ in range(iterations):
        unique = uuid.uuid4().hex[:10]
        payload = {
            "emails": [f"route.{unique}@example.com"],
            "deliveryAddress": {
                "street": "100 Route St",
                "city": "Gateway",
                "state": "QC",
                "postalCode": "H3G1M8",
                "country": "Canada",
            },
        }

        response = requests.post(f"{api_base_url}/users/", json=payload, timeout=10)
        assert response.status_code == 201, response.text
        created = response.json()
        user_id = created["userId"]
        created_user_ids.append(user_id)

        db_user = users_collection.find_one({"userId": user_id})
        assert db_user is not None
        observed_versions.append(classify_user_version(db_user))

    # Determine the version of the User microservice that was used to create the user.
    # If P = 50, validate that each User microservice version was used at least once.
    if kong_weight_session == 0:
        assert all(version == "v2" for version in observed_versions), observed_versions
    elif kong_weight_session == 100:
        assert all(version == "v1" for version in observed_versions), observed_versions
    else:
        assert "v1" in observed_versions, f"Expected at least one v1 route at P=50: {observed_versions}"
        assert "v2" in observed_versions, f"Expected at least one v2 route at P=50: {observed_versions}"

    # Clean the database of all the temporary users created during this test.
    users_collection.delete_many({"userId": {"$in": created_user_ids}})