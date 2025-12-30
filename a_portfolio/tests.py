from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from a_users.models import Profile
from .models import Category, Photo


class PhotoVisibilityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.owner_profile, _ = Profile.objects.get_or_create(user=self.owner)
        self.friend = User.objects.create_user(username="friend", password="pass")
        self.friend_profile, _ = Profile.objects.get_or_create(user=self.friend)
        self.category = Category.objects.create(name="Travel")

        self.public_photo = Photo.objects.create(
            owner=self.owner,
            title="Public",
            image="portfolio/test.jpg",
            visibility=Photo.VISIBILITY_PUBLIC,
            category=self.category,
        )
        self.friend_photo = Photo.objects.create(
            owner=self.owner,
            title="Friends only",
            image="portfolio/test2.jpg",
            visibility=Photo.VISIBILITY_FRIENDS,
            category=self.category,
        )
        self.friend_photo.allowed_friends.add(self.friend_profile)
        self.client = Client()

    def test_public_photo_visible_to_anonymous(self):
        resp = self.client.get(reverse("portfolio"))
        self.assertContains(resp, "Public")

    def test_friends_photo_visible_to_friend(self):
        self.client.login(username="friend", password="pass")
        resp = self.client.get(reverse("portfolio-detail", args=[self.friend_photo.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_friends_photo_forbidden_to_anonymous(self):
        resp = self.client.get(reverse("portfolio-detail", args=[self.friend_photo.pk]))
        self.assertEqual(resp.status_code, 403)

# Create your tests here.
