from django.urls import path

from . import views

app_name = "share"

urlpatterns = [
    path("share/new/", views.transfer_create, name="create"),
    path("share/<uuid:token>/", views.transfer_enter_code, name="enter-code"),
    path("share/<uuid:token>/resend/", views.transfer_resend_code, name="resend-code"),
    path("share/access/", views.transfer_email_code, name="email-code"),
    path("share/access/resend/", views.transfer_email_resend_code, name="email-resend-code"),
    path("share/<uuid:token>/download/<int:file_id>/", views.transfer_download, name="download-file"),
    path("share/<uuid:token>/finish/", views.transfer_finish, name="finish"),
]


