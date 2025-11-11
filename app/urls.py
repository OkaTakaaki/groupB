from django.urls import path
from . import views

urlpatterns = [
    path("home", views.home, name="home"),
    path("student_information", views.student_information, name="student_information"),
    path("mail_list", views.mail_list, name="mail_list"),
    path("calendar", views.calendar, name="calendar"),
    path("setting", views.setting, name="setting"),
]