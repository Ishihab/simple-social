import pytest

from bs4 import BeautifulSoup


async def test_user_profile_page_contains_expected_elements(authed_normal_user_client):
    user_me_response = await authed_normal_user_client.get("/users/me")
    user_id = user_me_response.json()["id"]
    assert user_me_response.status_code == 200

    response = await authed_normal_user_client.get(f"/users/profile/{user_id}")
    assert response.status_code == 200

    soup = BeautifulSoup(response.text, 'html.parser')

    profile_card = soup.find('div', {'id': 'profile-card'})
    assert profile_card is not None

    username_element = profile_card.find('p', {'id': 'profile-username'})
    display_name_element = profile_card.find('h1', {'id': 'profile-display-name'})


    assert username_element is not None
    assert display_name_element is not None

