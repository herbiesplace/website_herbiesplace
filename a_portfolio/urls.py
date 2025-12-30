from django.urls import path
from a_portfolio import views

urlpatterns = [
    path("portfolio/", views.portfolio_list, name="portfolio"),
    path("portfolio/private/", views.portfolio_private, name="portfolio-private"),
    path("portfolio/mine/", views.my_portfolio, name="portfolio-mine"),
    path("portfolio/user/<str:username>/", views.user_portfolio, name="portfolio-user"),
    path("portfolio/upload/", views.photo_create, name="portfolio-upload"),
    path("portfolio/bulk-delete/", views.photo_bulk_delete, name="portfolio-bulk-delete"),
    path("portfolio/categories/new/", views.category_create, name="portfolio-category-new"),
    path("portfolio/<int:pk>/", views.photo_detail, name="portfolio-detail"),
    path("portfolio/<int:pk>/edit/", views.photo_update, name="portfolio-edit"),
    path("portfolio/<int:pk>/delete/", views.photo_delete, name="portfolio-delete"),
    path("portfolio/<int:pk>/like/", views.photo_like, name="portfolio-like"),
    path("portfolio/<int:pk>/comment/", views.comment_create, name="portfolio-comment"),
    path("portfolio/<int:pk>/comment/<int:comment_id>/delete/", views.comment_delete, name="portfolio-comment-delete"),
]

