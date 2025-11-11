from django.urls import path
from . import views

urlpatterns = [
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('scaccount', views.scaccount, name='scaccount'),
    path('tcaccount', views.tcaccount, name='tcaccount'),
    path('student', views.student_select, name='student_select'),
    path('student/<int:student_id>/edit/', views.seaccount, name='seaccount'),
    path('teacher', views.teacher_select, name='teacher_select'),
    path('teacher/<int:teacher_id>/edit/', views.teaccount, name='teaccount'),
]
