from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path("attendance/today/", views.attendance_today, name="attendance_today"),
    path('student_parent/menu/', views.student_parent_menu, name='student_parent_menu'),
    path('student_information/', views.student_information, name='student_information'),
    path('<int:year>/<int:month>/', views.CalendarMonthView.as_view(), name='calendar_month'),
    path('calendar/', views.CalendarMonthView.as_view(), name='calendar_month'),
    path('day/<int:year>/<int:month>/<int:day>/', views.CalendarDayView.as_view(), name='calendar_day'),
    path('schedule/new/', views.ScheduleCreateView.as_view(), name='schedule_create'),
    path('schedule/<int:pk>/edit/', views.ScheduleUpdateView.as_view(), name='schedule_edit'),
    path('schedule/<int:pk>/delete/', views.ScheduleDeleteView.as_view(), name='schedule_delete'),
    path("setting", views.setting, name="setting"),
    path("mail_list/", views.mail_list, name="mail_list"),
    path("mail/<int:user_id>/", views.mail_list, name="mail_detail"), 
    path('smenu', views.smenu_view, name='smenu'),
    path('osirase/', views.osirase, name='osirase'),
    path("qr/", views.qr_page, name="qr_page"),
    path("qr/scan/", views.qr_attendance, name="qr_attendance"),
    path("verify-password/", views.verify_password, name="verify_password"),
    path("timeslots/", views.timeslot_list, name="timeslot_list"),
    path("timeslots/create/", views.timeslot_create, name="timeslot_create"),
    path("timeslot/<int:pk>/delete/", views.timeslot_delete, name="timeslot_delete"),
] 
