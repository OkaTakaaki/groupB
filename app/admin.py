from django.contrib import admin
from .models import (
    Parent,
    Student,
    Teacher,
    Schedule,
    Message,
    TimeSlot,
    StudentAttendanceRule,
    Attendance,
)

# =========================
# 保護者モデル
# =========================
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'login_id', 'phone')
    search_fields = ('name', 'login_id')
    ordering = ('id',)
    list_per_page = 20


# =========================
# 生徒モデル
# =========================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'child_name',
        'parent_name',
        'parent_login_id',
        'birth_date',
        'gender',
        'school_name',
        'address',
        'created_at',
    )

    # 保護者氏名
    def parent_name(self, obj):
        return obj.parent.name if obj.parent else "未設定"
    parent_name.admin_order_field = 'parent__name'
    parent_name.short_description = '保護者氏名'

    # 保護者ログインID
    def parent_login_id(self, obj):
        return obj.parent.login_id if obj.parent else "未設定"
    parent_login_id.admin_order_field = 'parent__login_id'
    parent_login_id.short_description = 'ログインID'


# =========================
# 基本出席ルール
# =========================
@admin.register(StudentAttendanceRule)
class StudentAttendanceRuleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'student',
        'day_of_week',
        'time_slot',   # ✅ ここだけ表示する
    )
    list_filter = ('day_of_week',)
    search_fields = ('student__child_name',)
    ordering = ('student', 'day_of_week')

# =========================
# 講師モデル
# =========================
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'login_id', 'name', 'permission_level', 'gender', 'created_at')
    search_fields = ('login_id', 'name')
    list_filter = ('permission_level', 'gender')
    ordering = ('-created_at',)
    list_per_page = 20


# =========================
# スケジュールモデル
# =========================
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'start_time', 'end_time', 'teacher', 'student_names')

    # ManyToManyField に対応
    def student_names(self, obj):
        return ", ".join(s.child_name for s in obj.students.all())
    student_names.short_description = '生徒氏名'


# =========================
# メッセージモデル
# =========================
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender_name', 'receiver_name', 'content_snippet', 'timestamp')

    def sender_name(self, obj):
        sender = obj.parent_sender or obj.teacher_sender
        return sender.name if sender else "不明"
    sender_name.short_description = '送信者'

    def receiver_name(self, obj):
        receiver = obj.parent_receiver or obj.teacher_receiver
        return receiver.name if receiver else "不明"
    receiver_name.short_description = '受信者'

    def content_snippet(self, obj):
        return obj.content[:30] + ("..." if len(obj.content) > 30 else "")
    content_snippet.short_description = '内容'


# =========================
# タイムスロットモデル
# =========================
@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time")

# =========================
# 出席記録モデル   
# =========================
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'date', 'time_slot', 'status')
    list_filter = ('date', 'status')
    search_fields = ('student__child_name',)
    ordering = ('-date', 'student')