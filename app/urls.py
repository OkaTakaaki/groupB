from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),  # ← 引数なしのchatページ
    path('chat/<int:user_id>/', views.chat_view, name='chat'),  # ← 引数ありバージョン
    path('home/', views.home_view, name='home'),
    path('users/', views.user_list_view, name='users'),
    path('messages/', views.message_list_view, name='messages'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('settings/', views.settings_view, name='settings'),
]
