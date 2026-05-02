from rest_framework.test import APITestCase

from .models import MyUser, Post


class SocialMediaApiTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.user = MyUser.objects.create_user(
            username="alice",
            password=self.password,
            email="alice@example.com",
            first_name="Alice",
            last_name="Anderson",
            bio="Hello from Alice",
        )
        self.other_user = MyUser.objects.create_user(
            username="bob",
            password=self.password,
            email="bob@example.com",
            first_name="Bob",
            last_name="Brown",
            bio="Hello from Bob",
        )

    def login_client(self, username="alice", password=None):
        response = self.client.post(
            "/api/token/",
            {"username": username, "password": password or self.password},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

        self.client.cookies["access_token"] = response.cookies["access_token"].value
        self.client.cookies["refresh_token"] = response.cookies["refresh_token"].value
        return response

    def test_register_creates_user(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "charlie",
                "email": "charlie@example.com",
                "first_name": "Charlie",
                "last_name": "Clark",
                "password": "AnotherStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(MyUser.objects.filter(username="charlie").exists())
        self.assertEqual(response.data["email"], "charlie@example.com")

    def test_login_sets_jwt_cookies(self):
        response = self.login_client()

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertEqual(response.data["user"]["username"], "alice")

    def test_authenticated_endpoint_uses_cookie_authentication(self):
        self.login_client()

        response = self.client.get("/api/authenticated/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, "authenticated!")

    def test_toggle_follow_follows_and_unfollows_user(self):
        self.login_client()

        follow_response = self.client.post(
            "/api/toggle_follow/",
            {"username": "bob"},
            format="json",
        )
        self.assertEqual(follow_response.status_code, 200)
        self.assertTrue(follow_response.data["now_following"])
        self.other_user.refresh_from_db()
        self.assertTrue(self.other_user.followers.filter(username="alice").exists())

        unfollow_response = self.client.post(
            "/api/toggle_follow/",
            {"username": "bob"},
            format="json",
        )
        self.assertEqual(unfollow_response.status_code, 200)
        self.assertFalse(unfollow_response.data["new_following"])
        self.other_user.refresh_from_db()
        self.assertFalse(self.other_user.followers.filter(username="alice").exists())

    def test_create_post_and_feed_endpoint_returns_post(self):
        self.login_client()

        create_response = self.client.post(
            "/api/create_post/",
            {"description": "My first post"},
            format="json",
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        feed_response = self.client.get("/api/get_posts/?page=1")
        self.assertEqual(feed_response.status_code, 200)
        self.assertEqual(feed_response.data["count"], 1)
        self.assertEqual(feed_response.data["results"][0]["description"], "My first post")
        self.assertFalse(feed_response.data["results"][0]["liked"])

    def test_toggle_like_updates_post_like_state(self):
        post = Post.objects.create(user=self.other_user, description="Bob's post")
        self.login_client()

        like_response = self.client.post(
            "/api/toggleLike/",
            {"id": post.id},
            format="json",
        )
        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(like_response.data["now_liked"])

        posts_response = self.client.get(f"/api/posts/{self.other_user.username}/")
        self.assertEqual(posts_response.status_code, 200)
        self.assertTrue(posts_response.data[0]["liked"])

        unlike_response = self.client.post(
            "/api/toggleLike/",
            {"id": post.id},
            format="json",
        )
        self.assertEqual(unlike_response.status_code, 200)
        self.assertFalse(unlike_response.data["now_liked"])

    def test_search_users_filters_by_username(self):
        self.login_client()

        response = self.client.get("/api/search/?query=bo")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["username"], "bob")

    def test_update_user_details_updates_profile_fields(self):
        self.login_client()

        response = self.client.patch(
            "/api/update_user/",
            {
                "bio": "Updated bio",
                "first_name": "Alicia",
                "email": "alicia@example.com",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, "Updated bio")
        self.assertEqual(self.user.first_name, "Alicia")
        self.assertEqual(self.user.email, "alicia@example.com")
