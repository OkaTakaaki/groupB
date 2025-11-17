from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path("home", views.home, name="home"),
    path("student_information", views.student_information, name="student_information"),
     # 月間カレンダー
    path('<int:year>/<int:month>/', views.CalendarMonthView.as_view(), name='calendar_month'),
    path('calendar/', views.CalendarMonthView.as_view(), name='calendar_month'),
 
    # 日別カレンダー
    path('day/<int:year>/<int:month>/<int:day>/', views.CalendarDayView.as_view(), name='calendar_day'),
 
    # スケジュール作成
    path('schedule/new/', views.ScheduleCreateView.as_view(), name='schedule_create'),
 
    # スケジュール編集
    path('schedule/<int:pk>/edit/', views.ScheduleUpdateView.as_view(), name='schedule_edit'),
 
    # スケジュール削除
    path('schedule/<int:pk>/delete/', views.ScheduleDeleteView.as_view(), name='schedule_delete'),
    
    path("setting", views.setting, name="setting"),
    path("mail_list/", views.mail_list, name="mail_list"),
    path("mail/<int:user_id>/", views.mail_list, name="mail_detail"),  
    path("qr", views.qr, name="qr"),
    path('smenu', views.smenu_view, name='smenu'),
]
