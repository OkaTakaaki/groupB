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
     # ✅ 予定（Schedule）に紐づく 生徒一覧ページ
    path("schedule/<int:pk>/students/", views.schedule_students, name="schedule_students"),
    # 生徒を追加
    path("schedule/<int:pk>/students/add/", views.schedule_student_add, name="schedule_student_add"),
    # 講師追加
    path("schedule/<int:pk>/teachers/add/", views.schedule_teacher_add, name="schedule_teacher_add"),
     # ✅ 振替登録ページ（元の授業 schedule と 対象の student を指定）
    path("schedule/<int:pk>/students/<int:student_id>/transfer/",views.transfer_register,name="transfer_register"),


] 
