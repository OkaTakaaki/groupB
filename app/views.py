from datetime import date, datetime, timedelta
import calendar
import locale
import jpholiday

# Django
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.core.files.base import ContentFile
from django import forms

# Models
from .models import (
    Schedule, Student, Parent, Teacher,
    Message, StudentAttendanceRule, Attendance,
    TimeSlot, StudentNotice
)

# Forms
from .forms import ScheduleForm, MessageForm



# ===============================
# メニュー
# ===============================
def student_parent_menu(request):
    user_type = request.session.get('user_type')
    user_id = request.session.get('user_id')

    notice_unread_count = 0
    mail_unread_count = 0
    student = None
    parent = None

    # 生徒ログイン
    if user_type == "student":
        student = Student.objects.filter(id=user_id).first()
        parent = student.parent if student else None

    # 保護者ログイン
    elif user_type == "parent":
        parent = Parent.objects.filter(id=user_id).first()
        student = Student.objects.filter(parent=parent).first()

    # ===== お知らせ未読件数 =====
    if student:
        notice_unread_count = StudentNotice.objects.filter(
            student=student,
            is_read=False
        ).count()

    # ===== メール未読件数 =====
    if parent:
        mail_unread_count = Message.objects.filter(
            parent_receiver=parent,
            is_read=False
        ).count()

    return render(request, 'student_parent_menu.html', {
        'user_type': user_type,
        'notice_unread_count': notice_unread_count,
        'mail_unread_count': mail_unread_count,
    })


# ===============================
# 生徒一覧
# ===============================
def student_information(request):
    if "user_id" not in request.session:
        return redirect("login")

    selected_day = request.GET.get("day")
    students = Student.objects.all()

    if selected_day:
        students = students.filter(
            attendance_rules__day_of_week=selected_day
        ).distinct()

    return render(request, "student_information.html", {
        "students": students,
        "selected_day": selected_day,
    })


# ===============================
# カレンダーTOP
# ===============================
def calendar_view(request):
    if 'user_id' not in request.session:
        return redirect('login')
    return render(request, 'calendar.html')


# ===============================
# 設定
# ===============================
def setting(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_type = request.session.get('user_type')
    user_id = request.session.get('user_id')

    teacher_level = None
    if user_type == 'teacher':
        teacher = Teacher.objects.get(id=user_id)
        teacher_level = teacher.permission_level

    context = {
        'user_type': user_type,
        'user_id': user_id,
        'teacher_level': teacher_level,
    }
    return render(request, 'setting.html', context)


# ===============================
# チャット
# ===============================
def mail_list(request, user_type=None, user_id=None):
    if 'user_id' not in request.session:
        return redirect('login')
 
    current_type = request.session['user_type']
    current_id = request.session['user_id']
 
    if current_type in ['student', 'parent']:
        current_user = get_object_or_404(Parent, id=current_id)
    else:
        current_user = get_object_or_404(Teacher, id=current_id)
 
    selected_day = request.GET.get("day")
    q = request.GET.get("q")
 
    weekdays = [
        ("Mon", "月曜日"),
        ("Tue", "火曜日"),
        ("Wed", "水曜日"),
        ("Thu", "木曜日"),
        ("Fri", "金曜日"),
        ("Sat", "土曜日"),
        ("Sun", "日曜日"),
    ]
 
    selected_user = None
    messages = []
 
    # ===== チャット相手 =====
    if user_id:
        if current_type in ['student', 'parent']:
            selected_user = get_object_or_404(Teacher, id=user_id)
        else:
            selected_user = get_object_or_404(Parent, id=user_id)
 
        if current_type in ['student', 'parent']:
            messages = Message.objects.filter(
                Q(parent_sender=current_user, teacher_receiver=selected_user) |
                Q(teacher_sender=selected_user, parent_receiver=current_user)
            ).order_by('timestamp')
        else:
            messages = Message.objects.filter(
                Q(teacher_sender=current_user, parent_receiver=selected_user) |
                Q(parent_sender=selected_user, teacher_receiver=current_user)
            ).order_by('timestamp')

        # ✅ 既読処理（チャットを開いたら相手からの未読を既読に）
        if current_type in ['student', 'parent']:
            Message.objects.filter(
                teacher_sender=selected_user,
                parent_receiver=current_user,
                is_read=False
            ).update(is_read=True)
        else:
            Message.objects.filter(
                parent_sender=selected_user,
                teacher_receiver=current_user,
                is_read=False
            ).update(is_read=True)
 
    # ===== メッセージ送信 =====
    if request.method == 'POST' and selected_user:
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
 
            if current_type in ['student', 'parent']:
                msg.parent_sender = current_user
                msg.teacher_receiver = selected_user
            else:
                msg.teacher_sender = current_user
                msg.parent_receiver = selected_user
 
            msg.save()
            return redirect('app:mail_detail', user_id=user_id)
    else:
        form = MessageForm()
 
    # ===== 左サイドのユーザー一覧 =====
    if current_type in ['student', 'parent']:
        users = Teacher.objects.all()
 
        if q:
            users = users.filter(name__icontains=q)
 
    else:
        users = Student.objects.all()
 
        if selected_day:
            users = users.filter(
                attendance_rules__day_of_week=selected_day
            ).distinct()
 
        if q:
            users = users.filter(
                child_name__icontains=q
            )

    # ===== 各ユーザーごとの未読件数 =====
    for user in users:
        if current_type in ['student', 'parent']:
            # 親 → 先生からの未読
            user.unread_count = Message.objects.filter(
                teacher_sender=user,
                parent_receiver=current_user,
                is_read=False
            ).count()
        else:
            # 先生 → 親からの未読
            user.unread_count = Message.objects.filter(
                parent_sender=user.parent,
                teacher_receiver=current_user,
                is_read=False
            ).count()
 
    context = {
        'users': users,
        'selected_day': selected_day,
        'weekdays': weekdays,
        'selected_user': selected_user,
        'messages': messages,
        'form': form,
        'current_user': current_user,
        'is_student': current_type == 'student',
        'user_type': current_type,
    }
 
    return render(request, 'mail_list.html', context) 


def smenu_view(request):
    template = loader.get_template("app/smenu.html")
    return HttpResponse(template.render({}, request))


# ===============================
# ロケール設定
# ===============================
try:
    locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
except:
    pass


# ===============================
# 月間カレンダー生成
# ===============================
def get_month_data(target_date):
    first_day = date(target_date.year, target_date.month, 1)
    last_day_of_month = date(
        target_date.year, target_date.month,
        calendar.monthrange(target_date.year, target_date.month)[1]
    )

    next_month = last_day_of_month + timedelta(days=1)
    prev_month = first_day - timedelta(days=1)

    start_day_of_calendar = first_day - timedelta(days=first_day.weekday())
    end_day_of_calendar = start_day_of_calendar + timedelta(days=41)

    schedules = Schedule.objects.filter(
        date__range=[start_day_of_calendar, end_day_of_calendar]
    ).select_related("teacher").prefetch_related("students")

    schedules_by_day = {}
    for s in schedules:
        d = s.date.isoformat()
        schedules_by_day.setdefault(d, []).append(s)

    calendar_days = []
    current_day = start_day_of_calendar
    for _ in range(42):
        calendar_days.append({
            'date': current_day,
            'weekday': current_day.weekday(),
            'is_current_month': current_day.month == target_date.month,
            'is_today': current_day == date.today(),
            'is_holiday': jpholiday.is_holiday(current_day),
            'holiday_name': jpholiday.is_holiday_name(current_day),
            'schedules': schedules_by_day.get(current_day.isoformat(), [])
        })
        current_day += timedelta(days=1)

    return {
        'year': target_date.year,
        'month': target_date.month,
        'month_name': target_date.strftime('%Y年%m月'),
        'target_date': target_date,
        'prev_month_url': reverse_lazy('app:calendar_month',
                                       kwargs={'year': prev_month.year, 'month': prev_month.month}),
        'next_month_url': reverse_lazy('app:calendar_month',
                                       kwargs={'year': next_month.year, 'month': next_month.month}),
        'calendar_days': calendar_days,
    }


# ===============================
# 月間カレンダー
# ===============================
class CalendarMonthView(View):
    def get(self, request, year=None, month=None):
        target_date = date(year, month, 1) if (year and month) else date.today()
        context = get_month_data(target_date)
        return render(request, 'app/calendar_month.html', context)


# ===============================
# 日間カレンダー
# ===============================
class CalendarDayView(View):
    def get(self, request, year, month, day):
        target_date = date(year, month, day)

        schedules = Schedule.objects.filter(
            date=target_date
        ).select_related("teacher").prefetch_related("students").order_by("start_time")

        # TimeSlot を取得
        time_slots = TimeSlot.objects.all().order_by("start_time")

        prev_day = target_date - timedelta(days=1)
        next_day = target_date + timedelta(days=1)

        context = {
            "target_date": target_date,
            "schedules": schedules,
            "time_slots": time_slots,
            "prev_day_url": reverse_lazy("app:calendar_day",
                                         kwargs={"year": prev_day.year, "month": prev_day.month, "day": prev_day.day}),
            "next_day_url": reverse_lazy("app:calendar_day",
                                         kwargs={"year": next_day.year, "month": next_day.month, "day": next_day.day}),
            "month_url": reverse_lazy("app:calendar_month",
                                      kwargs={"year": year, "month": month}),
        }
        return render(request, "app/calendar_day.html", context)


# ===============================
# スケジュール作成
# ===============================
class ScheduleCreateView(CreateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = "app/event_form.html"

    def get_success_url(self):
        s = self.object
        return reverse("app:calendar_month",
                       kwargs={"year": s.date.year, "month": s.date.month})


# ===============================
# スケジュール更新
# ===============================
class ScheduleUpdateView(UpdateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = "app/event_form.html"

    def get_success_url(self):
        s = self.get_object()
        return reverse("app:calendar_day",
                       kwargs={"year": s.date.year, "month": s.date.month, "day": s.date.day})


# ===============================
# スケジュール削除
# ===============================
class ScheduleDeleteView(DeleteView):
    model = Schedule
    template_name = "app/event_confirm_delete.html"

    def get_success_url(self):
        today = date.today()
        return reverse("app:calendar_month",
                       kwargs={"year": today.year, "month": today.month})


# ===============================
# お知らせ
# ===============================
def osirase(request):
    if 'user_id' not in request.session:
        return redirect('login')

    search = request.GET.get('q', '')
    if search:
        notices = Notice.objects.filter(
            Q(title__icontains=search) | Q(date__icontains=search)
        ).order_by('-date')
    else:
        notices = Notice.objects.all().order_by('-date')

    return render(request, 'osirase.html', {'notices': notices, 'search': search})


# ===============================
# QR 出席
# ===============================
def qr_page(request):
    today = timezone.now().date()

    attendances = Attendance.objects.filter(date=today)

    weekday_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_week = weekday_map[timezone.now().weekday()]

    scheduled_students = Student.objects.filter(
        attendance_rules__day_of_week=today_week
    ).distinct()

    attended_ids = attendances.values_list("student_id", flat=True)

    return render(request, "app/qr_reader.html", {
        "attendances": attendances,
        "scheduled_students": scheduled_students,
        "attended_ids": attended_ids,
    })


def qr_attendance(request):
    email = request.GET.get("email")

    if not email:
        return JsonResponse({"status": "error", "message": "メールアドレスが取得できません"})

    try:
        student = Student.objects.get(parent__login_id=email)
    except Student.DoesNotExist:
        return JsonResponse({"status": "error", "message": "未登録ユーザーです"})

    today = timezone.now().date()
    weekday_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_week = weekday_map[timezone.now().weekday()]

    # ✅ 今日の曜日のルールを取得
    rule = StudentAttendanceRule.objects.filter(
        student=student,
        day_of_week=today_week
    ).select_related("time_slot").first()

    attendance, created = Attendance.objects.get_or_create(
        student=student,
        date=today,
        defaults={
            "status": "present",
            "time_slot": rule.time_slot if rule else None
        }
    )

    if not created:
        attendance.status = "present"
        # 既存データに time_slot が無ければ補完
        if not attendance.time_slot and rule:
            attendance.time_slot = rule.time_slot
        attendance.save()

    return JsonResponse({
        "status": "success",
        "student": student.child_name,
        "time_slot": str(attendance.time_slot) if attendance.time_slot else "未設定",
        "message": "出席登録しました"
    })


def attendance_today(request):
    if not request.session.get("reauth_ok"):
        return redirect("app:qr_page")

    # request.session["reauth_ok"] = False

    today = timezone.now().date()

    weekday_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_week = weekday_map[timezone.now().weekday()]

    # ✅ 追加：選択された時間帯
    selected_slot = request.GET.get("slot")

    rules_today = StudentAttendanceRule.objects.select_related(
        "student",
        "time_slot"
    ).filter(
        day_of_week=today_week
    )

    # ✅ 追加：時間帯で絞り込み
    if selected_slot:
        rules_today = rules_today.filter(time_slot_id=selected_slot)

    rules_today = rules_today.order_by("time_slot__start_time")

    # ✅ 時間帯ボタン用（重複なし）
    time_slots_today = TimeSlot.objects.filter(
        studentattendancerule__day_of_week=today_week
    ).distinct().order_by("start_time")



    transfer_schedules = Schedule.objects.filter(
        date=today,
        status="振替"
    ).prefetch_related("students")

    transfer_students = []
    for schedule in transfer_schedules:
        for student in schedule.students.all():
            transfer_students.append({
                "student": student,
                "original_date": schedule.date,
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
            })

    attendances = Attendance.objects.filter(date=today)
    attended_ids = set(attendances.values_list('student_id', flat=True))

    return render(request, "teacher_attendance_list.html", {
    "rules_today": rules_today,
    "time_slots_today": time_slots_today,
    "selected_slot": selected_slot, 
    "transfer_students": transfer_students,
    "attendances": attendances,
    "attended_ids": attended_ids,
    "today": today,
})



# ===============================
# 再認証API
# ===============================
def verify_password(request):
    if request.method != "POST":
        return JsonResponse({"status": "error"})

    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")

    if not user_id:
        return JsonResponse({"status": "not_logged_in"})

    password = request.POST.get("password")

    if user_type == "teacher":
        user = get_object_or_404(Teacher, id=user_id)
    elif user_type in ["student", "parent"]:
        user = get_object_or_404(Parent, id=user_id)
    else:
        return JsonResponse({"status": "error"})

    if check_password(password, user.password_hash):
        request.session["reauth_ok"] = True
        request.session.modified = True
        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "fail"})

# =========================
# 時間帯モデル 
#========================
class TimeSlotForm(forms.ModelForm):
    class Meta:
        model = TimeSlot
        fields = ["name", "start_time", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

def timeslot_create(request):
    if request.method == "POST":
        form = TimeSlotForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("app:timeslot_list")   # 登録後一覧へ
    else:
        form = TimeSlotForm()

    return render(request, "app/timeslot_form.html", {
        "form": form
    })

def timeslot_list(request):
    timeslots = TimeSlot.objects.all().order_by("start_time")
    return render(request, "app/timeslot_list.html", {
        "timeslots": timeslots
    })
from .models import Student, StudentNotice



def tuuchi(request):
    if 'user_id' not in request.session:
        return redirect('login')

    if request.session.get('user_type') != 'teacher':
        messages.error(request, "権限がありません")
        return redirect('app:setting')

    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")
        is_important = bool(request.POST.get("is_important"))
        attachment = request.FILES.get("attachment")

        expire_at_str = request.POST.get("expire_at")
        expire_at = None
        if expire_at_str:
            expire_at = datetime.strptime(expire_at_str, "%Y-%m-%d")

        students = Student.objects.filter(parent__isnull=False)

        for student in students:
            file_copy = None

            if attachment:
                attachment.seek(0)
                file_copy = ContentFile(attachment.read(), name=attachment.name)

            StudentNotice.objects.create(
                student=student,
                title=title,
                message=message,
                is_important=is_important,
                expire_at=expire_at,
                attachment=file_copy,
            )

        messages.success(request, "通知を送信しました")
        return redirect("app:tuuchi")

    return render(request, "app/tuuchi.html")

#通知閲覧
def student_notice_list(request):
    if 'user_id' not in request.session:
        return redirect("login")

    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")

    if user_type not in ["student", "parent"]:
        return redirect("login")

    parent = get_object_or_404(Parent, id=user_id)
    student = get_object_or_404(Student, parent=parent)

    notices = StudentNotice.objects.filter(
        student=student
    ).filter(
        Q(expire_at__isnull=True) | Q(expire_at__gte=timezone.now())
    ).order_by(
        "-is_important",
        "-created_at"
    )

    # ✅ 未読件数（必要なら表示用）
    unread_count = notices.filter(is_read=False).count()

    return render(request, "app/student_notice_list.html", {
        "notices": notices,
        "unread_count": unread_count,
    })


#通知詳細
def student_notice_detail(request, notice_id):
    if 'user_id' not in request.session:
        return redirect("login")

    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")

    if user_type not in ["student", "parent"]:
        return redirect("login")

    if user_type == "student":
        student = get_object_or_404(Student, id=user_id)
    else:
        parent = get_object_or_404(Parent, id=user_id)
        student = get_object_or_404(Student, parent=parent)

    notice = get_object_or_404(
        StudentNotice,
        id=notice_id,
        student=student
    )

    # ✅ 既読にする
    if not notice.is_read:
        notice.is_read = True
        notice.save()

    return render(request, "app/student_notice_detail.html", {
        "notice": notice
    })


# ===============================
# お知らせ共通処理
# ===============================

def attendance_today(request):
    if not request.session.get("reauth_ok"):
        return redirect("app:qr_page")

    # request.session["reauth_ok"] = False

    today = timezone.now().date()

    weekday_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_week = weekday_map[timezone.now().weekday()]

    # 選択された時間帯を取得
    selected_slot = request.GET.get("slot")
    if selected_slot:
        try:
            selected_slot = int(selected_slot)
        except ValueError:
            selected_slot = None

    # 出席ルールを取得
    rules_today = StudentAttendanceRule.objects.select_related(
        "student",
        "time_slot"
    ).filter(day_of_week=today_week)

    # ✅ 時間帯で絞り込み
    if selected_slot:
        rules_today = rules_today.filter(time_slot_id=selected_slot)

    rules_today = rules_today.order_by("time_slot__start_time")

    # 出席済みの生徒ID
    attendances = Attendance.objects.filter(date=today)
    attended_ids = set(attendances.values_list('student_id', flat=True))

    # 時間帯ボタン用
    time_slots_today = TimeSlot.objects.filter(
        studentattendancerule__day_of_week=today_week
    ).distinct().order_by("start_time")

    # お知らせ（重要＋期限対応）
    limit_date = timezone.now() - timedelta(days=30)
    notices = StudentNotice.objects.filter(
        created_at__gte=limit_date
    ).filter(
        Q(expire_at__isnull=True) | Q(expire_at__gte=timezone.now())
    ).order_by(
        "-is_important",
        "-created_at"
    )

    return render(request, "teacher_attendance_list.html", {
        "rules_today": rules_today,
        "attendances": attendances,
        "attended_ids": attended_ids,
        "today": today,
        "notices": notices,
        "time_slots_today": time_slots_today,
        "selected_slot": selected_slot,
    })


def notice_delete(request, notice_id):
    notice = get_object_or_404(StudentNotice, id=notice_id)
    notice.delete()
    return JsonResponse({'success': True})

def timeslot_delete(request, pk):
    timeslot = get_object_or_404(TimeSlot, pk=pk)

    if request.method == "POST":
        timeslot.delete()
        return redirect("app:timeslot_list")

    return render(request, "app/timeslot_confirm_delete.html", {
        "timeslot": timeslot
    })
