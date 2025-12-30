from django.db import models
from django.conf import settings
from django.utils.text import slugify
from a_users.models import Profile


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    is_adult_only = models.BooleanField(
        default=False,
        help_text="Only visible to users 18+ who have adult content enabled. Staff only."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Photo(models.Model):
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_AUTH = "authenticated"
    VISIBILITY_FRIENDS = "friends"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, "Public"),
        (VISIBILITY_AUTH, "Authenticated users"),
        (VISIBILITY_FRIENDS, "Friends only"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="portfolio/")
    captured_on = models.DateField(blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photos",
    )
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
    )
    allowed_friends = models.ManyToManyField(
        Profile,
        blank=True,
        related_name="shared_with_me",
        help_text="Visible to these friends when visibility is friends-only.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-captured_on", "-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def image_url(self):
        return self.image.url if self.image else ""
    
    def get_like_count(self):
        return self.likes.count()
    
    def get_comment_count(self):
        return self.comments.count()
    
    def is_liked_by(self, user):
        if not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()


class Like(models.Model):
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="photo_likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["photo", "user"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} likes {self.photo.title}"


class Comment(models.Model):
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="photo_comments",
    )
    content = models.TextField()
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="If this is a reply to another comment",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} on {self.photo.title}"
    
    def get_reply_count(self):
        return self.replies.count()
