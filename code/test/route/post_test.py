from bs4 import BeautifulSoup


async def test_post_create_and_delete(
    authed_normal_user_client, authed_user_2_client, authed_user_post
):
    post_data = {"content": "This is a test post."}
    post_response = await authed_user_2_client.post("/posts", data=post_data)
    assert post_response.status_code == 200
    soup = BeautifulSoup(post_response.text, "html.parser")
    post_card = soup.find("div", {"id": "post_card_body"})
    second_user_post_id = post_card["data-post-id"]
    assert post_card is not None

    faild_delete_response = await authed_normal_user_client.delete(
        f"/posts/{second_user_post_id}"
    )
    assert faild_delete_response.status_code == 404

    first_user_post_id = authed_user_post["post_id"]
    delete_response = await authed_normal_user_client.delete(
        f"/posts/{first_user_post_id}"
    )
    assert delete_response.status_code == 200


async def test_post_like_and_unlike(
    authed_normal_user_client, authed_user_2_client, authed_user_post
):
    like_response = await authed_user_2_client.post(
        f"/posts/{authed_user_post['post_id']}/like"
    )
    assert like_response.status_code == 200
    like_soup = BeautifulSoup(like_response.text, "html.parser")
    is_liked = like_soup.find("button", {"id": "like-btn"})["data-response"]
    assert is_liked == "True"

    unlike_response = await authed_user_2_client.post(
        f"/posts/{authed_user_post['post_id']}/like"
    )
    assert unlike_response.status_code == 200
    unlike_soup = BeautifulSoup(unlike_response.text, "html.parser")
    is_unliked = unlike_soup.find("button", {"id": "like-btn"})["data-response"]
    assert is_unliked == "False"


async def test_feed_contains_post(
    authed_normal_user_client, authed_user_2_client, authed_user_post
):
    feed_response = await authed_normal_user_client.get("/feed")
    assert feed_response.status_code == 200
    feed_soup = BeautifulSoup(feed_response.text, "html.parser")
    post_card = feed_soup.find("div", {"id": "post_card_body"})
    assert post_card is not None
