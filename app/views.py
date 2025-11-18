from datetime import date, timedelta, datetime, time
import calendar
import locale
import jpholiday  # ★祝日判定（追加）

# Django
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, FormView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse
from django.template import loader
from django.db.models import *

# Local Imports
from .models import Schedule, Student, Parent, Teacher, Message
from .forms import ScheduleForm, MessageForm


from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import FormView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from datetime import date, timedelta, datetime, time 
import calendar
import locale
import jpholiday   # ★祝日判定（追加）

from .models import Schedule
from .forms import ScheduleForm
from django.views.generic import TemplateView

from django.db.models import Q
from .models import Notice  # ← 追加

#ホーム
def home(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす

    # ログインユーザー情報取得
    current_type = request.session['user_type']
    current_id = request.session['user_id']

    print(f'-------------------------{current_type} : {current_id}-------------------------')
    # 生徒の場合 → メニュー画面へリダイレクト
    if current_type == 'student':
        return redirect('smenu')  # ← URL名に合わせて変更
    context = {
        'user_type': current_type,
        'user_id': current_id,
    }

    return render(request, 'home.html', context)

#生徒
def student_information(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')  # ログイン画面へ飛ばす
    return render(request, 'student_information.html')

#カレンダー
def calendar_view(request):
    if 'user_id' not in request.session:
        return redirect('login')
    return render(request, 'calendar.html')

#設定
def setting(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_type = request.session.get('user_type')  # 'student', 'parent', 'teacher', 'admin'など
    user_id = request.session.get('user_id')

    # 教師モデルなどからparent情報を取得
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


#チャット
def mail_list(request, user_type=None, user_id=None):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす

    # ログインユーザー情報取得
    current_type = request.session['user_type']
    current_id = request.session['user_id']

    if current_type == 'student'or current_type == 'parent':
        current_user = get_object_or_404(Student, id=current_id)
    else:
        current_user = get_object_or_404(Teacher, id=current_id)

    # チャット相手
    selected_user = None
    messages = []

    if user_id:  # user_type は不要
        if current_type == 'student' or current_type == 'parent':
            current_user = get_object_or_404(Student, id=current_id)
            if user_id:
                selected_user = get_object_or_404(Teacher, id=user_id)
        elif current_type == 'teacher':
            current_user = get_object_or_404(Teacher, id=current_id)
            if user_id:
                selected_user = get_object_or_404(Student, id=user_id)
        else:
            # parent などログイン不可ユーザーはリダイレクト
            return redirect('home')

        # メッセージ取得
        if current_type == 'student' or current_type == 'parent':
            messages = Message.objects.filter(
                Q(student_sender=current_user, teacher_receiver=selected_user) |
                Q(teacher_sender=selected_user, student_receiver=current_user)
            ).order_by('timestamp')
        else:
            messages = Message.objects.filter(
                Q(teacher_sender=current_user, student_receiver=selected_user) |
                Q(student_sender=selected_user, teacher_receiver=current_user)
            ).order_by('timestamp')

    # メッセージ送信処理
    if request.method == 'POST' and selected_user:
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)

            # sender / receiver をモデルに合わせる
            if current_type == 'student' or current_type == 'parent':
                msg.student_sender = current_user
                msg.teacher_receiver = selected_user
            else:
                msg.teacher_sender = current_user
                msg.student_receiver = selected_user

            msg.save()
            return redirect('app:mail_detail', user_id=user_id)  # ← 名前空間 'app:' を追加


    else:
        form = MessageForm()

    # ユーザー一覧（チャット可能な相手）

    query = request.GET.get('q', '')
    if current_type == 'student' or current_type == 'parent':
        users = Teacher.objects.all()
        if query:
            users = users.filter(name__icontains=query)
        
    else:
        users = Student.objects.all()
        if query:
            users = users.filter(name__icontains=query)

    context = {
        'users': users,
        'selected_user': selected_user,
        'messages': messages,
        'form': form,
        'current_user': current_user,
        'is_student': current_type == 'student'
    }

    return render(request, 'mail_list.html', context)

def qr(request):
    return render(request, 'app/qr.html', {"user_id": 2})

def smenu_view(request):
    template = loader.get_template("app/smenu.html")
    return HttpResponse(template.render({}, request))

# ロケール設定
try:
    locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
except:
    pass

def get_month_data(target_date):
    """月間カレンダーデータを生成"""

# ロケール設定
try:
    locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
except:
    pass


# ===============================
# ★ 月間カレンダー生成関数
# ===============================
def get_month_data(target_date):
    """月間カレンダーデータを生成"""

    first_day = date(target_date.year, target_date.month, 1)
    last_day_of_month = date(
        target_date.year, target_date.month,
        calendar.monthrange(target_date.year, target_date.month)[1]
    )

    next_month = last_day_of_month + timedelta(days=1)
    prev_month = first_day - timedelta(days=1)

    # ★ 週の始まりを日曜日に調整したカレンダー
    start_day_of_calendar = first_day - timedelta(days=first_day.weekday())
    end_day_of_calendar = start_day_of_calendar + timedelta(days=41)

    # ★★★ 修正：ManyToMany → prefetch_related を使用
    schedules = Schedule.objects.filter(
        date__range=[start_day_of_calendar, end_day_of_calendar]
    ).select_related("teacher").prefetch_related("students")  # ← 修正

    schedules_by_day = {}
    for s in schedules:
        d = s.date.isoformat()
        schedules_by_day.setdefault(d, []).append(s)

    # 日付データ生成
    calendar_days = []
    current_day = start_day_of_calendar
    for _ in range(42):
        calendar_days.append({
            'date': current_day,
            'weekday': current_day.weekday(),
            'is_current_month': current_day.month == target_date.month,
            'is_today': current_day == date.today(),

            # ★ 祝日判定の追加
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
    """日間カレンダー"""
    def get(self, request, year, month, day):
        target_date = date(year, month, day)

        # ★★★ 修正：ManyToMany 対応 & スケジュールを取得
        schedules = Schedule.objects.filter(
            date=target_date
        ).select_related("teacher").prefetch_related("students").order_by("start_time")

        # ★★★ 追加：0〜23時の時間リストを作る
        hours = list(range(24))  # 0〜23

        prev_day = target_date - timedelta(days=1)
        next_day = target_date + timedelta(days=1)

        context = {
            "target_date": target_date,
            "schedules": schedules,
            "hours": hours,   # ← ★追加（Time Line 用）
            "prev_day_url": reverse_lazy("app:calendar_day",
                                         kwargs={"year": prev_day.year, "month": prev_day.month, "day": prev_day.day}),
            "next_day_url": reverse_lazy("app:calendar_day",
                                         kwargs={"year": next_day.year, "month": next_day.month, "day": next_day.day}),
            "month_url": reverse_lazy("app:calendar_month",
                                      kwargs={"year": year, "month": month}),
        }
        return render(request, "app/calendar_day.html", context)



# ===============================
# ★ スケジュール作成
# ===============================
class ScheduleCreateView(FormView):
    model = Schedule
    form_class = ScheduleForm
    template_name = "app/event_form.html"
    success_url = reverse_lazy("app:calendar_month")

    # ---------------------------
    # ★ 初期値を URL から設定
    # ---------------------------
    def get_initial(self):
        initial = super().get_initial()

        # --- 授業日 ---
        date_param = self.request.GET.get("date")
        if date_param:
            try:
                parsed_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                initial["date"] = parsed_date
            except:
                pass

        # --- 開始時刻 ---
        start_param = self.request.GET.get("start")  # "5:00"
        if start_param:
            try:
                parsed_time = datetime.strptime(start_param, "%H:%M").time()
                initial["start_time"] = parsed_time

                # 終了時刻を 1時間後に自動設定
                dt = datetime.combine(datetime.today(), parsed_time)
                end_time = (dt + timedelta(hours=1)).time()
                initial["end_time"] = end_time
            except:
                pass

        return initial

    # ---------------------------
    # ★ 保存処理
    # ---------------------------
    def form_valid(self, form):
        schedule = form.save(commit=False)

        # ▼▼▼ ドロップダウンの時刻を Time型に ▼▼▼
        start_hour = form.cleaned_data['start_hour']
        start_minute = form.cleaned_data['start_minute']
        end_hour = form.cleaned_data['end_hour']
        end_minute = form.cleaned_data['end_minute']

        schedule.start_time = time(int(start_hour), int(start_minute))
        schedule.end_time = time(int(end_hour), int(end_minute))

        # URLの日付をセット
        date_param = self.request.GET.get("date")
        date_param = self.request.GET.get("date")
        if date_param:
            try:
                # ISO形式（YYYY-MM-DD）を想定
                schedule.date = datetime.strptime(date_param, "%Y-%m-%d").date()
            except ValueError:
                # フォーマットが違う場合は無視するか、今日の日付をセット
                schedule.date = date.today()

        schedule.save()
        form.save_m2m()

        return super().form_valid(form)



# ===============================
# 予定更新
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
# 予定削除
# ===============================
class ScheduleDeleteView(DeleteView):
    model = Schedule
    template_name = "app/event_confirm_delete.html"

    def get_success_url(self):
        return reverse("app:calendar_month")
# お知らせ一覧
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
