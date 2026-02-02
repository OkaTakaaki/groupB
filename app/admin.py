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
    ScheduleStudent,
    StudentNotice
)

# =========================
# 保護者モデル
# =========================
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    """
    保護者（Parent）を管理する管理画面設定。
    """
    list_display = ("id", "name", "login_id", "phone")
    search_fields = ("name", "login_id")
    ordering = ("id",)
    list_per_page = 20


# =========================
# 生徒モデル
# =========================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """
    生徒（Student）を管理する管理画面設定。
    保護者情報も一緒に確認できるように表示項目を拡張。
    """
    list_display = (
        "id",
        "child_name",
        "parent_name",
        "parent_login_id",
        "birth_date",
        "gender",
        "school_name",
        "address",
        "created_at",
    )
    search_fields = ("child_name", "child_name_kana", "parent__name", "parent__login_id")
    list_filter = ("gender",)
    ordering = ("id",)

    def parent_name(self, obj):
        """関連する保護者の氏名を表示（未設定の場合は表示を固定）"""
        return obj.parent.name if obj.parent else "未設定"
    parent_name.admin_order_field = "parent__name"
    parent_name.short_description = "保護者氏名"

    def parent_login_id(self, obj):
        """関連する保護者のログインID（メール）を表示"""
        return obj.parent.login_id if obj.parent else "未設定"
    parent_login_id.admin_order_field = "parent__login_id"
    parent_login_id.short_description = "ログインID"


# =========================
# 基本出席ルール
# =========================
@admin.register(StudentAttendanceRule)
class StudentAttendanceRuleAdmin(admin.ModelAdmin):
    """
    生徒ごとの基本出席ルール（曜日＋時間帯）を管理する管理画面設定。
    """
    list_display = ("id", "student", "day_of_week", "time_slot")
    list_filter = ("day_of_week",)
    search_fields = ("student__child_name",)
    ordering = ("student", "day_of_week")



# =========================
# 講師モデル
# =========================
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    """
    講師（Teacher）を管理する管理画面設定。
    """
    list_display = ("id", "login_id", "name", "permission_level", "gender", "created_at")
    search_fields = ("login_id", "name", "name_kana")
    list_filter = ("permission_level", "gender")
    ordering = ("-created_at",)
    list_per_page = 20


# =========================
# スケジュールモデル
# =========================
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'start_time', 'end_time', 'teacher', 'student_names')

    def student_names(self, obj):
        return ", ".join(s.child_name for s in obj.students.all())
    student_names.short_description = '生徒氏名'


# =========================
# メッセージモデル
# =========================
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'sender_name',
        'receiver_name',
        'content_snippet',
        'is_read',  
        'timestamp',
    )

    list_filter = ('is_read', 'timestamp')
    search_fields = ('content',)

    def sender_name(self, obj):
        """送信者（親or講師）を表示"""
        sender = obj.parent_sender or obj.teacher_sender
        return sender.name if sender else "不明"
    sender_name.short_description = "送信者"

    def receiver_name(self, obj):
        """受信者（親or講師）を表示"""
        receiver = obj.parent_receiver or obj.teacher_receiver
        return receiver.name if receiver else "不明"
    receiver_name.short_description = "受信者"

    def content_snippet(self, obj):
        """本文の先頭だけを一覧に表示（長すぎる場合は省略）"""
        return obj.content[:30] + ("..." if len(obj.content) > 30 else "")
    content_snippet.short_description = "内容"


# =========================
# タイムスロットモデル
# =========================
@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    """
    時間帯（TimeSlot）を管理する管理画面設定。
    """
    list_display = ("id", "name", "start_time", "end_time")
    ordering = ("start_time",)



# =========================
# 出席記録モデル
# =========================
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    """
    出席記録（Attendance）を管理する管理画面設定。
    """
    list_display = ("id", "student", "date", "time_slot", "status")
    list_filter = ("date", "status")
    search_fields = ("student__child_name",)
    ordering = ("-date", "student")


# =========================
# スケジュール × 生徒（中間テーブル）
# =========================
@admin.register(ScheduleStudent)
class ScheduleStudentAdmin(admin.ModelAdmin):
    """
    授業ごとの生徒の状態（予定・出席・欠席・振替など）を管理する。
    ここが「同じ予定で A君は出席、B君は欠席…」を実現する中心。
    """
    list_display = ("id", "schedule", "student", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("student__child_name",)
    ordering = ("-updated_at",)


# =========================
# Schedule に中間テーブルを表示する Inline
# =========================
class ScheduleStudentInline(admin.TabularInline):
    """
    Schedule の管理画面内で、
    生徒＋ステータス（ScheduleStudent）を表形式で表示・編集できるようにする。
    """
    model = ScheduleStudent
    extra = 0


# =========================
# スケジュールモデル（Inline対応版）
# =========================
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    """
    授業予定（Schedule）を管理する管理画面設定。
    - 一覧：生徒名をまとめて表示
    - 詳細：ScheduleStudent（中間テーブル）をInlineで編集
    """
    list_display = ("id", "date", "start_time", "end_time", "teacher", "student_names")
    inlines = [ScheduleStudentInline]
    ordering = ("-date", "start_time")

    def student_names(self, obj):
        """
        Schedule に紐づく生徒の名前をカンマ区切りで一覧表示する。
        ※ through を使っていても obj.students.all() は取得できる。
        """
        return ", ".join(s.child_name for s in obj.students.all())
    student_names.short_description = "生徒氏名"
    list_display = ('id', 'student', 'date', 'time_slot', 'status')
    list_filter = ('date', 'status')
    search_fields = ('student__child_name',)
    ordering = ('-date', 'student')


# =========================
# 生徒お知らせモデル（⭐重要・期限・添付対応）
# =========================
@admin.register(StudentNotice)
class StudentNoticeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "title",
        "is_important",     # ⭐ 追加
        "expire_at",        # ⭐ 追加
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
