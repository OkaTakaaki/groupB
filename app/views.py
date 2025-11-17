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
        if date_param:
            schedule.date = date_param

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


# ===============================
# ホーム画面
# ===============================
class HomeView(TemplateView):
    template_name = "app/home.html"
