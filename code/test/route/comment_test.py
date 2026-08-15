from bs4 import BeautifulSoup


async def test_comment_create_and_delete(
    authed_normal_user_client, authed_user_2_client, authed_user_post
):
    comment_data = {
        "content": "This is a test comment.",
        "post_id": authed_user_post["post_id"],
    }
    response = await authed_user_2_client.post(
        f"/posts/{authed_user_post['post_id']}/comments", data=comment_data
    )
    assert response.status_code == 200
    user_2_comment_soup = BeautifulSoup(response.text, "html.parser")
    user_2_comment_card = user_2_comment_soup.find("li", {"data": "comment-body"})
    data_post_id = user_2_comment_card["data-post-id"]
    assert data_post_id == authed_user_post["post_id"]
    assert user_2_comment_card is not None

    second_user_comment_id = user_2_comment_card["data-comment-id"]
    failed_delete_response = await authed_normal_user_client.delete(
        f"/posts/{authed_user_post['post_id']}/comments/{second_user_comment_id}"
    )
    assert failed_delete_response.status_code == 404

    first_user_comment_id = authed_user_post["comment_id"]
    delete_response = await authed_normal_user_client.delete(
        f"/posts/{authed_user_post['post_id']}/comments/{first_user_comment_id}"
    )
    assert delete_response.status_code == 200
