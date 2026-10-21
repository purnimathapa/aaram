"""Khalti payment URLs."""
from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("khalti/start/<str:number>/", views.start, name="start"),
    path("khalti/callback/", views.callback, name="callback"),
]
