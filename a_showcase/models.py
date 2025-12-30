from django.db import models


class ShowcaseImage(models.Model):
    image = models.ImageField(upload_to="showcase/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.image.name or f"Showcase image {self.pk}"


