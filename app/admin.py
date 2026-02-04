from django.contrib import admin
from .models import (
    Parent,
    Student,
    Teacher,
    TimeSlot,
    Attendance,
    StudentAttendanceRule,
    Schedule,
    ScheduleStudent,
    ScheduleTeacher,
    Message,
    StudentNotice,
    TeacherAttendanceRule
)

# =========================
# 保護者
# =========================
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "login_id", "phone")
    search_fields = ("name", "login_id")
    ordering = ("id",)
    list_per_page = 20


# =========================
# 生徒
# =========================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "child_name",
        "parent_name",
        "parent_login_id",
        "birth_date",
        "gender",
        "school_name",
        "created_at",
    )
    search_fields = (
        "child_name",
        "child_name_kana",
        "parent__name",
        "parent__login_id",
    )
    list_filter = ("gender",)
    ordering = ("id",)

    def parent_name(self, obj):
        return obj.parent.name if obj.parent else "未設定"
    parent_name.short_description = "保護者氏名"

    def parent_login_id(self, obj):
        return obj.parent.login_id if obj.parent else "未設定"
    parent_login_id.short_description = "ログインID"


# =========================
# 講師
# =========================
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "login_id",
        "name",
        "permission_level",
        "gender",
        "created_at",
    )
    search_fields = ("login_id", "name", "name_kana")
    list_filter = ("permission_level", "gender")
    ordering = ("-created_at",)


# =========================
# 時間帯
# =========================
@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "start_time", "end_time")
    ordering = ("start_time",)


# =========================
# 出席記録
# =========================
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "date", "time_slot", "status")
    list_filter = ("date", "status")
    search_fields = ("student__child_name",)
    ordering = ("-date",)


# =========================
# 基本出席ルール
# =========================
@admin.register(StudentAttendanceRule)
class StudentAttendanceRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "day_of_week", "time_slot")
    list_filter = ("day_of_week",)
    search_fields = ("student__child_name",)
    ordering = ("student", "day_of_week")

# =========================
# 講師 出勤ルール
# =========================
@admin.register(TeacherAttendanceRule)
class TeacherAttendanceRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "teacher",
        "day_of_week",
        "time_slot",
        "is_primary",
    )
    list_filter = ("day_of_week", "is_primary")
    search_fields = ("teacher__name",)
    ordering = ("teacher", "day_of_week", "time_slot")


# =========================
# Schedule × 生徒（Inline）
# =========================
class ScheduleStudentInline(admin.TabularInline):
    model = ScheduleStudent
    extra = 0


# =========================
# Schedule × 講師（Inline）
# =========================
class ScheduleTeacherInline(admin.TabularInline):
    model = ScheduleTeacher
    extra = 0


# =========================
# 授業スケジュール
# =========================
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "date",
        "start_time",
        "end_time",
        "teacher",
        "student_names",
        "status",
    )
    list_filter = ("date", "status")
    ordering = ("-date", "start_time")
    inlines = [ScheduleStudentInline, ScheduleTeacherInline]

    def student_names(self, obj):
        return ", ".join(s.child_name for s in obj.students.all())
    student_names.short_description = "生徒氏名"


# =========================
# メッセージ
# =========================
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender_name",
        "receiver_name",
        "content_snippet",
        "is_read",
        "timestamp",
    )
    list_filter = ("is_read", "timestamp")
    search_fields = ("content",)
    ordering = ("-timestamp",)

    def sender_name(self, obj):
        sender = obj.parent_sender or obj.teacher_sender
        return sender.name if sender else "不明"
    sender_name.short_description = "送信者"

    def receiver_name(self, obj):
        receiver = obj.parent_receiver or obj.teacher_receiver
        return receiver.name if receiver else "不明"
    receiver_name.short_description = "受信者"

    def content_snippet(self, obj):
        return obj.content[:30] + ("..." if len(obj.content) > 30 else "")
    content_snippet.short_description = "内容"


# =========================
# 生徒お知らせ
# =========================
@admin.register(StudentNotice)
class StudentNoticeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "title",
        "is_important",
        "expire_at",
        "is_read",
        "created_at",
    )
    list_filter = (
        "is_important",
        "is_read",
        "expire_at",
        "created_at",
    )
    search_fields = (
        "title",
        "message",
        "student__child_name",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    fieldsets = (
        ("基本情報", {
            "fields": ("student", "title", "message", "attachment")
        }),
        ("公開設定", {
            "fields": ("is_important", "expire_at")
        }),
        ("状態", {
            "fields": ("is_read", "created_at")
        }),
    )
