import os
import csv
import pytest
import requests

EXPECTED_TWO_OBJECTS_RESPONSE_MSG = "Expected [original_user, updated_user] response..."
EXPECTED_TWO_OBJECTS_COUNT_MSG = "Expected exactly two objects in the response..."
UPDATED_USER_MISSING_MSG = "The updated user is missing from the database..."
UPDATED_ORDER_MISSING_MSG = "The order associated with the user is missing from the database..."


def _get_existing_user_and_order(mongo_client):
    db = mongo_client[os.getenv("DATABASE_NAME")]
    users_collection = db["users"]
    orders_collection = db["orders"]

    db_user = users_collection.find_one({})
    assert db_user is not None, f"No users exist in the {os.getenv('DATABASE_NAME')}..."

    db_user_id = db_user["userId"]
    db_order = orders_collection.find_one({"userId": db_user_id})
    assert db_order is not None, f"No orders exist for user {db_user_id}..."

    return users_collection, orders_collection, db_user, db_user_id

# TC_03
def test_tc03_user_integration(api_base_url, mongo_client):
    # Load the databse, as well as the users and orders collections.
    users_collection, orders_collection, db_user, db_user_id = _get_existing_user_and_order(mongo_client)

    # Store the original state of the user's email/delivery address.
    original_email_addresses = db_user['emails']
    original_delivery_address = db_user['deliveryAddress']

    # Create the new values for email/delivey address.
    updated_email_address = ["updated@example.com"]
    updated_delivery_address = {
        "street": "123 Updated Street",
        "city": "Updated City",
        "state": "Updated State",
        "postalCode": "U1U2U3",
        "country": "Updated Country"
    }

    # Create the payload for the PUT request.
    payload = {
        "emails": updated_email_address,
        "deliveryAddress": updated_delivery_address
    }

    # Create the PUT request
    put_response = requests.put(
        f"{api_base_url}/users/{db_user_id}",
        json=payload
    )

    # Assertions to verify the state of the data after the PUT request.
    assert put_response.status_code == 200, f"PUT failed: {put_response.text}"
    response_body = put_response.json()
    assert isinstance(response_body, list), EXPECTED_TWO_OBJECTS_RESPONSE_MSG
    assert len(response_body) == 2, EXPECTED_TWO_OBJECTS_COUNT_MSG

    original_user = response_body[0]
    updated_user = response_body[1]

    assert original_user["userId"] == db_user_id
    assert original_user["emails"] == original_email_addresses
    assert original_user["deliveryAddress"] == original_delivery_address

    assert updated_user["userId"] == db_user_id
    assert updated_user["emails"] == updated_email_address
    assert updated_user["deliveryAddress"] == updated_delivery_address

    # Assertions to validate that the data in MongoDB has been updated.
    updated_db_user = users_collection.find_one({"userId": db_user_id})
    assert updated_db_user is not None, UPDATED_USER_MISSING_MSG
    assert updated_db_user["emails"] == updated_email_address
    assert updated_db_user["deliveryAddress"] == updated_delivery_address

    updated_db_order = orders_collection.find_one({"userId": db_user_id})
    assert updated_db_order is not None, UPDATED_ORDER_MISSING_MSG
    assert updated_db_order["userId"] == db_user_id
    assert updated_db_order["userEmails"] == updated_email_address
    assert updated_db_order["deliveryAddress"] == updated_delivery_address


def test_tc03_user_update_emails_only(api_base_url, mongo_client):
    # Load the databse, as well as the users and orders collections.
    users_collection, orders_collection, db_user, db_user_id = _get_existing_user_and_order(mongo_client)

    # Store the original state of the user's email/delivery address.
    original_email_addresses = db_user["emails"]
    original_delivery_address = db_user["deliveryAddress"]

    # Create the payload for the PUT request with only updated emails.
    updated_email_address = ["updated.emails.only@example.com"]
    payload = {"emails": updated_email_address}

    # Create the PUT request
    put_response = requests.put(
        f"{api_base_url}/users/{db_user_id}",
        json=payload
    )

    # Assertions to verify the state of the data after the PUT request.
    assert put_response.status_code == 200, f"PUT failed: {put_response.text}"
    response_body = put_response.json()
    assert isinstance(response_body, list), EXPECTED_TWO_OBJECTS_RESPONSE_MSG
    assert len(response_body) == 2, EXPECTED_TWO_OBJECTS_COUNT_MSG

    original_user = response_body[0]
    updated_user = response_body[1]

    assert original_user["emails"] == original_email_addresses
    assert original_user["deliveryAddress"] == original_delivery_address
    assert updated_user["emails"] == updated_email_address
    assert updated_user["deliveryAddress"] == original_delivery_address

    # Assertions to validate that the data in MongoDB has been updated.
    updated_db_user = users_collection.find_one({"userId": db_user_id})
    assert updated_db_user is not None, UPDATED_USER_MISSING_MSG
    assert updated_db_user["emails"] == updated_email_address
    assert updated_db_user["deliveryAddress"] == original_delivery_address

    updated_db_order = orders_collection.find_one({"userId": db_user_id})
    assert updated_db_order is not None, UPDATED_ORDER_MISSING_MSG
    assert updated_db_order["userEmails"] == updated_email_address
    assert updated_db_order["deliveryAddress"] == original_delivery_address


def test_tc03_user_update_delivery_address_only(api_base_url, mongo_client):
    # Load the database, as well as the users and orders collections.
    users_collection, orders_collection, db_user, db_user_id = _get_existing_user_and_order(mongo_client)

    # Store the original state of the user's email/delivery address.
    original_email_addresses = db_user["emails"]
    original_delivery_address = db_user["deliveryAddress"]

    # Create the payload for the PUT request with only updated delivery address.
    updated_delivery_address = {
        "street": "123 Address Only Street",
        "city": "Address City",
        "state": "Address State",
        "postalCode": "A1A1A1",
        "country": "Address Country"
    }
    payload = {"deliveryAddress": updated_delivery_address}

    # Create the PUT request
    put_response = requests.put(
        f"{api_base_url}/users/{db_user_id}",
        json=payload
    )

    # Assertions to verify the state of the data after the PUT request.
    assert put_response.status_code == 200, f"PUT failed: {put_response.text}"
    response_body = put_response.json()
    assert isinstance(response_body, list), EXPECTED_TWO_OBJECTS_RESPONSE_MSG
    assert len(response_body) == 2, EXPECTED_TWO_OBJECTS_COUNT_MSG

    original_user = response_body[0]
    updated_user = response_body[1]

    assert original_user["emails"] == original_email_addresses
    assert original_user["deliveryAddress"] == original_delivery_address
    assert updated_user["emails"] == original_email_addresses
    assert updated_user["deliveryAddress"] == updated_delivery_address

    # Assertions to validate that the data in MongoDB has been updated.
    updated_db_user = users_collection.find_one({"userId": db_user_id})
    assert updated_db_user is not None, UPDATED_USER_MISSING_MSG
    assert updated_db_user["emails"] == original_email_addresses
    assert updated_db_user["deliveryAddress"] == updated_delivery_address

    updated_db_order = orders_collection.find_one({"userId": db_user_id})
    assert updated_db_order is not None, UPDATED_ORDER_MISSING_MSG
    assert updated_db_order["userEmails"] == original_email_addresses
    assert updated_db_order["deliveryAddress"] == updated_delivery_address


def load_invalid_payloads_from_csv():
    csv_file = os.path.join(os.path.dirname(__file__), "tc03.csv")
    payloads = []

    with open(csv_file, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            payload = {}

            emails_raw = (row.get("emails") or "").strip()
            if emails_raw:
                payload["emails"] = [e.strip() for e in emails_raw.split(";") if e.strip()]

            delivery_address = {}
            for field in ["street", "city", "state", "postalCode", "country"]:
                value = (row.get(field) or "").strip()
                if value:
                    delivery_address[field] = value

            if delivery_address:
                payload["deliveryAddress"] = delivery_address

            first_name = (row.get("firstName") or "").strip()
            if first_name:
                payload["firstName"] = first_name

            payloads.append(payload)

    return payloads


@pytest.mark.parametrize(
    "invalid_payload",
    load_invalid_payloads_from_csv(),
)
def test_tc03_user_update_invalid_payload(api_base_url, mongo_client, invalid_payload):
    # Load the database, as well as the users and orders collections.
    users_collection, _, _, db_user_id = _get_existing_user_and_order(mongo_client)
    user_before = users_collection.find_one({"userId": db_user_id})
    assert user_before is not None, "User missing before invalid PUT test..."

    # Create the PUT request with the invalid payload
    put_response = requests.put(
        f"{api_base_url}/users/{db_user_id}",
        json=invalid_payload,
    )

    # Assertions to verify that the invalid PUT request is rejected.
    assert put_response.status_code == 400, (
        f"Expected 400 for invalid payload {invalid_payload}, got "
        f"{put_response.status_code}: {put_response.text}"
    )

    # Assertions to validate that the data in MongoDB has not been updated.
    user_after = users_collection.find_one({"userId": db_user_id})
    assert user_after is not None, "User missing after invalid PUT test..."
    assert user_after["emails"] == user_before["emails"]
    assert user_after["deliveryAddress"] == user_before["deliveryAddress"]