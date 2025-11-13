from django.contrib import admin
from .models import Parent, Student, Teacher, Schedule

class ParentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'login_id', 'phone', 'created_at')
    search_fields = ('name', 'login_id')
    ordering = ('-created_at',)
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
        'login_id',
        'birth_date',
        'gender',
        'school_name',
        'address',
        'created_at'
    )
    # parent_name をメソッドとして定義
    def parent_name(self, obj):
        return obj.parent.name
    parent_name.admin_order_field = 'parent__name'  # ソート可能にする
    parent_name.short_description = '保護者氏名'

    #ログインID
    def login_id(self, obj):
        return obj.parent.login_id
    login_id.admin_order_field = 'parent__login_id'
    login_id.short_description = 'ログインID'


# =========================
# 講師モデル
# =========================
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'login_id', 'name', 'permission_level',
        'gender', 'created_at'
    )
    search_fields = ('login_id', 'name')
    list_filter = ('permission_level', 'gender')
    ordering = ('-created_at',)
    list_per_page = 20


# =========================
# スケジュールモデル
# =========================
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'date', 'start_time', 'end_time',
        'teacher', 'student', 'status'
    )
    list_filter = ('date', 'status', 'teacher')
    search_fields = ('teacher__name', 'student__child_name')
    ordering = ('-date',)
    list_per_page = 20
