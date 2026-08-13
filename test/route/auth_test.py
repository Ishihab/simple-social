import pytest
from bs4 import BeautifulSoup

async def test_register_page_contains_expected_elements(async_normal_user_client):
    response = await async_normal_user_client.get("/auth/register")
    assert response.status_code == 200

    soup = BeautifulSoup(response.text, 'html.parser')


    form = soup.find('form', {'id': 'register-form'})
    assert form is not None


    email_input = form.find('input', {'name': 'email'})
    password_input = form.find('input', {'name': 'password'})
    username_input = form.find('input', {'name': 'username'})
    display_name_input = form.find('input', {'name': 'display_name'})

    assert email_input is not None
    assert password_input is not None
    assert username_input is not None
    assert display_name_input is not None

async def test_login_page_contains_expected_elements(async_normal_user_client):
    response = await async_normal_user_client.get("/auth/login")
    assert response.status_code == 200

    soup = BeautifulSoup(response.text, 'html.parser')

    form = soup.find('form', {'id': 'login-form'})
    assert form is not None

    username_input = form.find('input', {'name': 'username'})
    password_input = form.find('input', {'name': 'password'})

    assert username_input is not None
    assert password_input is not None

async def test_register_user_and_login(async_normal_user_client):
    # Register a new user
    register_data = {
        "email": "testuser@example.com",
        "password": "password123",
        "username": "testuser",
        "display_name": "Test User"
    }
    response = await async_normal_user_client.post("/auth/register", json=register_data)
    assert response.status_code == 201
    json_response = response.json()
    assert json_response["email"] == "testuser@example.com"
    assert json_response["username"] == "testuser"
    assert json_response["display_name"] == "Test User"
    assert json_response["is_superuser"] is False
    assert "password" not in json_response  

    login_data = {
        "username": json_response["email"],
        "password": "password123"
    }
    response = await async_normal_user_client.post("/auth/cookie/login", data=login_data)
    assert response.status_code == 204