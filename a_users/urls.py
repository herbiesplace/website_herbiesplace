from django.urls import path
from a_users.views import *
from a_users import admin_views

urlpatterns = [
    path('', profile_view, name="profile"),
    path('edit/', profile_edit_view, name="profile-edit"),
    path('onboarding/', profile_edit_view, name="profile-onboarding"),
    path('settings/', profile_settings_view, name="profile-settings"),
    path('dob-change/', dob_change_request_view, name="dob-change-request"),
    path('emailchange/', profile_emailchange, name="profile-emailchange"),
    path('emailverify/', profile_emailverify, name="profile-emailverify"),
    path('delete/', profile_delete_view, name="profile-delete"),
    path('friends/', friends_view, name="friends"),
    path('friends/request/<int:user_id>/', friend_request_send, name="friend-request-send"),
    path('friends/request/<int:request_id>/accept/', friend_request_accept, name="friend-request-accept"),
    path('friends/request/<int:request_id>/decline/', friend_request_decline, name="friend-request-decline"),
    path('friends/<str:username>/', friend_detail, name="friend-detail"),
    path('messages/', messages_view, name="messages"),
    path('messages/<str:username>/', message_thread, name="message-thread"),
    # Admin routes
    path('admin/', admin_views.admin_dashboard, name="admin-dashboard"),
    path('admin/users/', admin_views.admin_users, name="admin-users"),
    path('admin/users/<int:user_id>/edit/', admin_views.admin_user_edit, name="admin-user-edit"),
    path('admin/users/<int:user_id>/delete/', admin_views.admin_user_delete, name="admin-user-delete"),
    path('admin/photos/', admin_views.admin_photos, name="admin-photos"),
    path('admin/photos/<int:photo_id>/edit/', admin_views.admin_photo_edit, name="admin-photo-edit"),
    path('admin/photos/<int:photo_id>/delete/', admin_views.admin_photo_delete, name="admin-photo-delete"),
    path('admin/photos/bulk-delete/', admin_views.admin_photos_bulk_delete, name="admin-photos-bulk-delete"),
    path('admin/comments/', admin_views.admin_comments, name="admin-comments"),
    path('admin/comments/<int:comment_id>/delete/', admin_views.admin_comment_delete, name="admin-comment-delete"),
    path('admin/categories/', admin_views.admin_categories, name="admin-categories"),
    path('admin/categories/<int:category_id>/edit/', admin_views.admin_category_edit, name="admin-category-edit"),
    path('admin/categories/<int:category_id>/delete/', admin_views.admin_category_delete, name="admin-category-delete"),
    path('admin/dob-requests/', admin_views.admin_dob_requests, name="admin-dob-requests"),
    path('admin/dob-requests/<int:req_id>/<str:decision>/', admin_views.admin_dob_request_resolve, name="admin-dob-request-resolve"),
]