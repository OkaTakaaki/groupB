from django.urls import path
from . import views

urlpatterns = [
    path("home", views.home, name="home"),
    path("student_information", views.student_information, name="student_information"),
    path("calendar", views.calendar, name="calendar"),
    path("setting", views.setting, name="setting"),
    path("mail_list", views.mail_list, name="mail_list"),
    path("mail/<int:user_id>/", views.mail_list, name="mail_detail"),  
    path('smenu', views.smenu_view, name='smenu'),
]
