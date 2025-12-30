from django.urls import path

from . import views

app_name = "showcase"

urlpatterns = [
    path("", views.showcase_list, name="list"),
    path("upload/", views.showcase_upload, name="upload"),
]


