from django.urls import path
from . import views

urlpatterns = [
    path('smenu', views.smenu_view, name='smenu'),
]
