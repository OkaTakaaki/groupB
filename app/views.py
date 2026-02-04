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
from django.views.decorators.http import require_http_methods
from django.db import transaction

# Models
from .models import (
    Schedule, Student, Parent, Teacher,
    Message, StudentAttendanceRule, Attendance,
    TimeSlot, StudentNotice,ScheduleStudent, ScheduleTeacher
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
def get_month_data(request, target_date):
    year = target_date.year
    month = target_date.month

    first_day = date(year, month, 1)
    last_day_of_month = date(
        year, month,
        calendar.monthrange(year, month)[1]
    )

    next_month = last_day_of_month + timedelta(days=1)
    prev_month = first_day - timedelta(days=1)

    start_day_of_calendar = first_day - timedelta(
        days=(first_day.weekday() + 1) % 7
    )
    end_day_of_calendar = start_day_of_calendar + timedelta(days=41)

    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")

    # ==========================
    # スケジュール取得（基本）
    # ==========================
    schedules = Schedule.objects.filter(
        date__range=[start_day_of_calendar, end_day_of_calendar]
    )

    # ==========================
    # ユーザー別の表示制御
    # ==========================
    if user_type == "student":
        student = Student.objects.filter(id=user_id).first()
        if student:
            schedules = schedules.filter(
                students=student
            ).exclude(
                student_links__student=student,
                student_links__status='振替',
                original_date__isnull=True
            )

    elif user_type == "parent":
        parent = Parent.objects.filter(id=user_id).first()
        student = Student.objects.filter(parent=parent).first()
        if student:
            schedules = schedules.filter(
                students=student
            ).exclude(
                student_links__student=student,
                student_links__status='振替',
                original_date__isnull=True
            )

    # teacher は何もしない（全件表示）

    schedules = schedules.distinct().select_related(
        "teacher"
    ).prefetch_related(
        "students"
    )

    # ==========================
    # 日付ごとにまとめる
    # ==========================
    schedules_by_day = {}
    for s in schedules:
        d = s.date.isoformat()
        schedules_by_day.setdefault(d, []).append(s)

    # ==========================
    # カレンダー42日分生成
    # ==========================
    calendar_days = []
    current_day = start_day_of_calendar

    for _ in range(42):
        calendar_days.append({
            'date': current_day,
            'weekday': (current_day.weekday() + 1) % 7,
            'is_current_month': current_day.month == target_date.month,
            'is_today': current_day == date.today(),
            'is_holiday': jpholiday.is_holiday(current_day),
            'holiday_name': jpholiday.is_holiday_name(current_day),
            'schedules': schedules_by_day.get(current_day.isoformat(), [])
        })
        current_day += timedelta(days=1)

    return {
        'year': year,
        'month': month,
        'month_name': target_date.strftime('%Y年%m月'),
        'target_date': target_date,
        'user_type': user_type,
        'prev_month_url': reverse_lazy(
            'app:calendar_month',
            kwargs={'year': prev_month.year, 'month': prev_month.month}
        ),
        'next_month_url': reverse_lazy(
            'app:calendar_month',
            kwargs={'year': next_month.year, 'month': next_month.month}
        ),
        'calendar_days': calendar_days,
    }


# ===============================
# 月間カレンダー
# ===============================
class CalendarMonthView(View):
    def get(self, request, year=None, month=None):
        target_date = date(year, month, 1) if (year and month) else date.today()

        # ✅ request を渡す
        context = get_month_data(request, target_date)

        return render(request, 'app/calendar_month.html', context)


# ===============================
# 日間カレンダー
# ===============================
class CalendarDayView(View):
    def get(self, request, year, month, day):
        target_date = date(year, month, day)

        schedules = Schedule.objects.filter(
            date=target_date
        )

        user_type = request.session.get("user_type")
        user_id = request.session.get("user_id")

        # ==========================
        # ★ 日表示では振替元を非表示
        # ==========================
        if user_type == "student":
            student = Student.objects.filter(id=user_id).first()
            if student:
                schedules = schedules.filter(
                    students=student
                ).exclude(
                    student_links__student=student,
                    student_links__status='振替',
                    original_date__isnull=True
                )

        elif user_type == "parent":
            parent = Parent.objects.filter(id=user_id).first()
            student = Student.objects.filter(parent=parent).first()
            if student:
                schedules = schedules.filter(
                    students=student
                ).exclude(
                    student_links__student=student,
                    student_links__status='振替',
                    original_date__isnull=True
                )

        # teacher は除外しない（管理上見せた方がいい）
        schedules = schedules.select_related("teacher").order_by("start_time").distinct()

        time_slots = TimeSlot.objects.all().order_by("start_time")

        # ✅ 空白を消すための表示範囲（最初〜最後のTimeSlot）
        first_slot = time_slots.first()
        start_offset = first_slot.start_time.hour * 60 + first_slot.start_time.minute if first_slot else 0

        last_slot = time_slots.last()
        end_offset = last_slot.end_time.hour * 60 + last_slot.end_time.minute if last_slot else start_offset + 60

        # ✅ ここ重要：各TimeSlotに「その枠の予定があるか」を持たせる
        slot_rows = []
        for slot in time_slots:
            found_list = schedules.filter(
                start_time=slot.start_time,
                end_time=slot.end_time
            )

            slot_rows.append({
                "slot": slot,
                "schedules": found_list,  # ← 複数！
            })

        prev_day = target_date - timedelta(days=1)
        next_day = target_date + timedelta(days=1)

        context = {
            'user_type': request.session.get("user_type"),
            "target_date": target_date,
            "slot_rows": slot_rows,    # ✅ テンプレで使う（重要）
            "start_offset": start_offset,
            "end_offset": end_offset,
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

    def get_initial(self):
        initial = super().get_initial()

        # date
        date_str = self.request.GET.get("date")
        if date_str:
            initial["date"] = date_str

        # ✅ start=HH:MM → TimeSlotのstart_timeと一致させて初期選択
        start_str = self.request.GET.get("start")
        if start_str:
            try:
                t = datetime.strptime(start_str, "%H:%M").time()
                slot = TimeSlot.objects.filter(start_time=t).first()
                if slot:
                    initial["time_slot"] = slot
            except ValueError:
                pass

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        date_str = self.request.GET.get("date")
        if not date_str and context.get("form") and context["form"].initial.get("date"):
            date_str = context["form"].initial.get("date")

        context["date_str"] = date_str
        return context

    def form_valid(self, form):
        self.object = form.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        s = self.object
        return reverse("app:calendar_day",
                       kwargs={"year": s.date.year, "month": s.date.month, "day": s.date.day})

# ===============================
# スケジュール更新
# ===============================
class ScheduleUpdateView(UpdateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = "app/event_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ✅ 編集は object.date を hidden に入れる
        obj = self.get_object()
        context["date_str"] = obj.date.strftime("%Y-%m-%d")
        return context

    def form_valid(self, form):
        self.object = form.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        s = self.object
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

@require_http_methods(["GET", "POST"])
def schedule_students(request, pk):
    """
    予定（Schedule）に紐づく
    - 生徒一覧（ScheduleStudent）
    - 講師一覧（ScheduleTeacher）
    を表示＆操作する画面
    """
    schedule = get_object_or_404(Schedule, pk=pk)

    # -----------------------------
    # POST：ボタン操作（更新/削除など）
    # -----------------------------
    if request.method == "POST":
        action = request.POST.get("action")

        # ✅ 生徒削除
        if action == "remove_student":
            student_id = request.POST.get("student_id")
            if student_id:
                ScheduleStudent.objects.filter(
                    schedule=schedule,
                    student_id=student_id
                ).delete()
            return redirect("app:schedule_students", pk=schedule.pk)

        # ✅ 生徒ステータス更新（振替は別ページへ）
        elif action == "update_student_status":
            student_id = request.POST.get("student_id")
            status = request.POST.get("status")

            if student_id and status:
                link = get_object_or_404(
                    ScheduleStudent,
                    schedule=schedule,
                    student_id=student_id
                )

                # ✅ 振替が選ばれたら別ページへ
                if status == "振替":
                    return redirect("app:transfer_register", pk=schedule.pk, student_id=student_id)

                # ✅ 振替以外は通常更新
                link.status = status
                link.save()

            return redirect("app:schedule_students", pk=schedule.pk)

        # ✅ 講師削除（ここでは student_id を一切使わない）
        elif action == "remove_teacher":
            teacher_id = request.POST.get("teacher_id")
            if teacher_id:
                ScheduleTeacher.objects.filter(
                    schedule=schedule,
                    teacher_id=teacher_id
                ).delete()
            return redirect("app:schedule_students", pk=schedule.pk)

        # ✅ 想定外の action の場合も安全に戻す
        return redirect("app:schedule_students", pk=schedule.pk)

    # -----------------------------
    # GET：画面表示
    # -----------------------------
    links = ScheduleStudent.objects.select_related("student").filter(
        schedule=schedule
    ).exclude(
        status='振替',
        schedule__original_date__isnull=True
    ).order_by("student__child_name")


    teacher_links = ScheduleTeacher.objects.select_related("teacher").filter(
        schedule=schedule
    ).order_by("teacher__name")
    login_parent = None
    if request.session.get("user_type") == "parent":
        login_parent = Parent.objects.get(id=request.session["user_id"])

    context = {
        "schedule": schedule,
        "target_date": schedule.date,
        "links": links,
        "teacher_links": teacher_links,
        "user_type": request.session.get("user_type"),
        "login_parent": login_parent,
        "status_choices": ScheduleStudent.STATUS_CHOICES,
    }
    return render(request, "app/schedule_students.html", context)

def send_transfer_notification(student, original_schedule, transfer_schedule):
    """
    振替確定時に教師へ自動通知
    """

    from_teacher_links = ScheduleTeacher.objects.filter(schedule=original_schedule)
    to_teacher_links = ScheduleTeacher.objects.filter(schedule=transfer_schedule)
    print("-------------------",from_teacher_links, to_teacher_links, "-------------------")

    from_msg_content = (
        "【振替通知（自動）】\n"
        f"{student.child_name}さんの授業が振替になりました。\n\n"
        "▼ 振替元授業\n"
        f"日付：{original_schedule.date.strftime('%Y年%m月%d日')}\n"
        f"時間：{original_schedule.start_time.strftime('%H:%M')}～"
        f"{original_schedule.end_time.strftime('%H:%M')}\n"
        f"生徒：{student.child_name}"
    )

    to_msg_content = (
        "【振替通知（自動）】\n"
        f"{student.child_name}さんが振替で参加します。\n\n"
        "▼ 振替先授業\n"
        f"日付：{transfer_schedule.date.strftime('%Y年%m月%d日')}\n"
        f"時間：{transfer_schedule.start_time.strftime('%H:%M')}～"
        f"{transfer_schedule.end_time.strftime('%H:%M')}\n"
        f"生徒：{student.child_name}"
    )

    # 振替元教師へ
    for link in from_teacher_links:
        Message.objects.create(
            teacher_receiver=link.teacher,
            content=from_msg_content,
            is_system=True,
        )

    # 振替先教師へ
    for link in to_teacher_links:
        Message.objects.create(
            teacher_receiver=link.teacher,
            content=to_msg_content,
            is_system=True,
        )


@require_http_methods(["GET", "POST"])
def schedule_student_add(request, pk):
    """
    生徒を検索して授業（Schedule）に追加するページ
    - GET : 生徒検索＋一覧表示
    - POST: 選択した生徒を ScheduleStudent で追加（重複は作らない）
    """
    schedule = get_object_or_404(Schedule, pk=pk)

    # 🔍 検索ワード
    q = request.GET.get("q", "").strip()

    # ✅ 全生徒（名前順）
    students_qs = Student.objects.all().order_by("child_name")

    # ✅ 検索（名前・かな）
    if q:
        students_qs = students_qs.filter(
            Q(child_name__icontains=q) |
            Q(child_name_kana__icontains=q)
        )

    # ✅ すでにこの授業に登録済みの生徒は除外
    already_ids = set(
        ScheduleStudent.objects.filter(schedule=schedule)
        .values_list("student_id", flat=True)
    )
    students = students_qs.exclude(id__in=already_ids)

    # ✅ 追加処理
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        if student_id:
            student = get_object_or_404(Student, pk=student_id)
            ScheduleStudent.objects.get_or_create(
                schedule=schedule,
                student=student,
                defaults={"status": "予定"}  # 最初は「予定」で登録
            )
        return redirect("app:schedule_students", pk=schedule.pk)

    # ✅ 画面表示
    return render(request, "app/schedule_student_add.html", {
        "schedule": schedule,
        "q": q,
        "students": students,
        "already_count": len(already_ids),
    })


@require_http_methods(["GET", "POST"])
def schedule_teacher_add(request, pk):
    """
    講師を検索して授業に追加するページ（未登録の講師だけ表示）
    - GET : 未登録の講師一覧（検索可）
    - POST: 選択した講師を ScheduleTeacher（中間モデル）で追加（重複は作らない）
    """
    schedule = get_object_or_404(Schedule, pk=pk)

    # 🔍 検索ワード
    q = request.GET.get("q", "").strip()

    # ✅ 全講師（名前順）
    teachers_qs = Teacher.objects.all().order_by("name")

    # ✅ 検索（名前・login_id・権限）
    if q:
        teachers_qs = teachers_qs.filter(
            Q(name__icontains=q) |
            Q(login_id__icontains=q) |
            Q(permission_level__icontains=q)
        )

    # ✅ すでにこの予定に登録されている講師ID（中間モデルから取得）
    already_ids = set(
        ScheduleTeacher.objects.filter(schedule=schedule)
        .values_list("teacher_id", flat=True)
    )

    # ✅ 未登録の講師だけ表示（＝画面がスッキリ）
    teachers = teachers_qs.exclude(id__in=already_ids)

    # ✅ 「現在の担当（複数）」表示用（テンプレで使う）
    teacher_links = ScheduleTeacher.objects.select_related("teacher").filter(
        schedule=schedule
    ).order_by("teacher__name")

    # ✅ 追加処理
    if request.method == "POST":
        teacher_id = request.POST.get("teacher_id")
        if teacher_id:
            teacher = get_object_or_404(Teacher, pk=teacher_id)

            # ✅ 二重追加を防ぐ（unique_together + get_or_create）
            ScheduleTeacher.objects.get_or_create(
                schedule=schedule,
                teacher=teacher
            )

        # ✅ 追加後は予定詳細へ戻る（追加結果がすぐ見える）
        return redirect("app:schedule_students", pk=schedule.pk)

    # ✅ 画面表示
    return render(request, "app/schedule_teacher_add.html", {
        "schedule": schedule,
        "q": q,
        "teachers": teachers,                 # 未登録だけ
        "already_count": len(already_ids),    # 登録済み人数（任意表示用）
        "teacher_links": teacher_links,       # 現在の担当表示用
    })

@require_http_methods(["GET", "POST"])
def transfer_register(request, pk, student_id):
    """
    振替登録ページ
    - 同じ日付×同じ時間帯に「振替Schedule」が既にあれば再利用
    - 振替確定時に教師へ自動通知
    """

    original_schedule = get_object_or_404(Schedule, pk=pk)
    student = get_object_or_404(Student, pk=student_id)

    # 元の授業にその生徒がいるかチェック
    link = get_object_or_404(ScheduleStudent, schedule=original_schedule, student=student)

    time_slots = TimeSlot.objects.all().order_by("start_time")

    if request.method == "POST":
        new_date_str = request.POST.get("new_date")
        slot_id = request.POST.get("time_slot")

        if not new_date_str or not slot_id:
            return render(request, "app/transfer_register.html", {
                "original": original_schedule,
                "student": student,
                "time_slots": time_slots,
                "error": "日付と時間帯を選択してください",
            })

        slot = get_object_or_404(TimeSlot, pk=slot_id)

        try:
            new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        except ValueError:
            return render(request, "app/transfer_register.html", {
                "original": original_schedule,
                "student": student,
                "time_slots": time_slots,
                "error": "日付の形式が正しくありません",
            })
        
        with transaction.atomic():

            # 振替Schedule取得 or 作成
            transfer_schedule, created = Schedule.objects.get_or_create(
                date=new_date,
                start_time=slot.start_time,
                end_time=slot.end_time,
                status="振替",
                defaults={
                    "title": f"{original_schedule.title}（振替）",
                    "original_date": original_schedule.date,
                }
            )

            # 講師を自動選択（基本ルール参照）
            teacher = select_teacher_for_transfer(new_date, slot)
            if teacher:
                ScheduleTeacher.objects.get_or_create(
                    schedule=transfer_schedule,
                    teacher=teacher
                )

            # 振替Scheduleに生徒を紐付け
            ScheduleStudent.objects.get_or_create(
                schedule=transfer_schedule,
                student=student,
                defaults={"status": "振替"}
            )

            # 元の授業側の生徒ステータスを振替にする
            link.status = "振替"
            link.save()

            # =============================
            # ✅ 振替通知を教師に送信
            # =============================
            send_transfer_notification(student, original_schedule, transfer_schedule)

            return redirect("app:schedule_students", pk=transfer_schedule.pk)

    return render(request, "app/transfer_register.html", {
        "original": original_schedule,
        "student": student,
        "time_slots": time_slots,
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

    # ✅ ログイン種別ごとに student を特定
    if user_type == "student":
        student = get_object_or_404(Student, id=user_id)

    elif user_type == "parent":
        parent = get_object_or_404(Parent, id=user_id)
        student = get_object_or_404(Student, parent=parent)

    else:
        return redirect("login")

    # ✅ 30日以内 + 期限切れ除外 + 生徒限定
    limit_date = timezone.now() - timedelta(days=30)
    notices = StudentNotice.objects.filter(
        student=student,
        created_at__gte=limit_date
    ).filter(
        Q(expire_at__isnull=True) | Q(expire_at__gte=timezone.now())
    ).order_by(
        "-is_important",
        "-created_at"
    )

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

    if user_type == "student":
        student = get_object_or_404(Student, id=user_id)

    elif user_type == "parent":
        parent = get_object_or_404(Parent, id=user_id)
        student = get_object_or_404(Student, parent=parent)

    else:
        return redirect("login")

    notice = get_object_or_404(
        StudentNotice,
        id=notice_id,
        student=student
    )

    # ✅ 既読処理
    if not notice.is_read:
        notice.is_read = True
        notice.save(update_fields=["is_read"])

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


# ===============================
# 月次 Schedule 自動生成（共通処理）
# ===============================
def generate_monthly_schedules(year: int, month: int):
    """
    StudentAttendanceRule を元に
    指定月の Schedule を自動生成する
    """
    created_count = 0

    first_day = date(year, month, 1)
    last_day = date(
        year, month,
        calendar.monthrange(year, month)[1]
    )

    rules = StudentAttendanceRule.objects.select_related(
        "student",
        "time_slot"
    )

    current_day = first_day
    while current_day <= last_day:
        weekday_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekday = weekday_map[current_day.weekday()]

        daily_rules = rules.filter(day_of_week=weekday)

        for rule in daily_rules:
            slot = rule.time_slot
            student = rule.student

            schedule, created = Schedule.objects.get_or_create(
                date=current_day,
                start_time=slot.start_time,
                end_time=slot.end_time,
                defaults={
                    "title": "授業予定",
                    "teacher": None,
                    "status": "予定",
                }
            )

            teacher = select_teacher_for_schedule(schedule)
            if teacher:
                ScheduleTeacher.objects.get_or_create(
                    schedule=schedule,
                    teacher=teacher
                )

            ScheduleStudent.objects.get_or_create(
                schedule=schedule,
                student=student,
                defaults={"status": "予定"}
            )

            if created:
                created_count += 1

        current_day += timedelta(days=1)

    return created_count

# ===============================
# 講師用：月次 Schedule 生成画面
# ===============================
class MonthlyScheduleGenerateView(View):

    def get(self, request):
        if "user_id" not in request.session:
            return redirect("login")

        if request.session.get("user_type") != "teacher":
            messages.error(request, "権限がありません")
            return redirect("app:setting")

        today = timezone.now().date()

        return render(request, "app/schedule_generate.html", {
            "default_year": today.year,
            "default_month": today.month,
            "years": [2024, 2025, 2026, 2027],
            "months": list(range(1, 13)),
        })
    
    def post(self, request):
        if request.session.get("user_type") != "teacher":
            messages.error(request, "権限がありません")
            return redirect("app:setting")

        try:
            year = int(request.POST.get("year"))
            month = int(request.POST.get("month"))
        except (TypeError, ValueError):
            messages.error(request, "年月の指定が不正です")
            return redirect("app:schedule_generate")

        created = generate_monthly_schedules(year, month)

        messages.success(
            request,
            f"{year}年{month}月のScheduleを {created} 件生成しました"
        )

        return redirect("app:calendar_month", year=year, month=month)


def select_teacher_for_schedule(schedule):
    """
    Schedule に自動で講師を1人割り当てる
    """
    teachers = Teacher.objects.all().order_by("-permission_level")

    for teacher in teachers:
        # 同時間帯・同日の重複チェック
        conflict = ScheduleTeacher.objects.filter(
            teacher=teacher,
            schedule__date=schedule.date,
            schedule__start_time=schedule.start_time,
            schedule__end_time=schedule.end_time,
        ).exists()

        if not conflict:
            return teacher

    return None


WEEKDAY_MAP = {
    "Mon": 0,
    "Tue": 1,
    "Wed": 2,
    "Thu": 3,
    "Fri": 4,
    "Sat": 5,
    "Sun": 6,
}


class ScheduleGenerateView(View):

    def get(self, request):
        if request.session.get("user_type") != "teacher":
            messages.error(request, "権限がありません")
            return redirect("app:setting")

        today = date.today()

        return render(request, "app/schedule_generate.html", {
            "default_year": today.year,
            "default_month": today.month,
            "years": [2024, 2025, 2026, 2027],
            "months": list(range(1, 13)),
        })
    
    def post(self, request):
        if request.session.get("user_type") != "teacher":
            messages.error(request, "権限がありません")
            return redirect("app:setting")

        year = int(request.POST.get("year"))
        month = int(request.POST.get("month"))

        # 担当講師（とりあえず実行した講師を自動割当）
        teacher = Teacher.objects.get(id=request.session["user_id"])

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        rules = StudentAttendanceRule.objects.select_related(
            "student",
            "time_slot"
        )

        created_count = 0
        skipped_count = 0

        current = first_day
        while current <= last_day:
            weekday = current.weekday()

            for rule in rules:
                if WEEKDAY_MAP[rule.day_of_week] != weekday:
                    continue

                slot = rule.time_slot
                if not slot:
                    continue

                # ✅ 既存Scheduleがあればスキップ
                schedule, created = Schedule.objects.get_or_create(
                    date=current,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    defaults={
                        "title": "通常授業",
                        "teacher": teacher,
                        "status": "予定",
                    }
                )

                if not created:
                    skipped_count += 1
                    continue

                # 生徒を紐づけ
                ScheduleStudent.objects.create(
                    schedule=schedule,
                    student=rule.student,
                    status="予定"
                )

                created_count += 1

            current += timedelta(days=1)

        messages.success(
            request,
            f"{year}年{month}月のスケジュールを生成しました "
            f"(新規: {created_count}件 / スキップ: {skipped_count}件)"
        )

        return redirect("app:calendar_month", year=year, month=month)
    

def select_teacher_for_transfer(date, time_slot):
    weekday_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday = weekday_map[date.weekday()]

    # 基本ルールに合う講師
    candidate_teachers = Teacher.objects.filter(
        attendance_rules__day_of_week=weekday,
        attendance_rules__time_slot=time_slot
    ).distinct().order_by("-permission_level")

    for teacher in candidate_teachers:
        # 同時間帯・同日の重複チェック
        conflict = ScheduleTeacher.objects.filter(
            teacher=teacher,
            schedule__date=date,
            schedule__start_time=time_slot.start_time,
            schedule__end_time=time_slot.end_time,
        ).exists()

        if not conflict:
            return teacher

    return None