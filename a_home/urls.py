from django.urls import path
from a_home.views import *

urlpatterns = [
    path('', home_view, name="home"),
    path('contact/', contact_view, name="contact"),
    path('search/', search_view, name="search"),
    path('trust-safety/', trust_safety_view, name="trust-safety"),
    path('terms/', terms_view, name="terms"),
]
