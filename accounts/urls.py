from django.urls import path
from . import views

urlpatterns = [
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('gcaccount', views.gcaccount, name='gcaccount'),
    path('tcaccount', views.tcaccount, name='tcaccount'),
]
