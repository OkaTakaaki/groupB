from .models import Message
from django import forms
from django.forms import DateInput
from .models import Schedule, Teacher, Student

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']  # ユーザーが入力するのは本文のみ
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'メッセージを入力'}),
        }


class ScheduleForm(forms.ModelForm):

    # ▼ Googleカレンダー風：時・分のドロップダウン
    start_hour = forms.ChoiceField(
        choices=[(str(i).zfill(2), str(i).zfill(2)) for i in range(24)],
        label="開始（時）"
    )
    start_minute = forms.ChoiceField(
        choices=[("00", "00"), ("15", "15"), ("30", "30"), ("45", "45")],
        label="開始（分）"
    )

    end_hour = forms.ChoiceField(
        choices=[(str(i).zfill(2), str(i).zfill(2)) for i in range(24)],
        label="終了（時）"
    )
    end_minute = forms.ChoiceField(
        choices=[("00", "00"), ("15", "15"), ("30", "30"), ("45", "45")],
        label="終了（分）"
    )

    class Meta:
        model = Schedule
        fields = ['teacher', 'students', 'status']
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-input'}),
            'students': forms.SelectMultiple(attrs={'class': 'form-input', 'size': 6}),
            'status': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ▼ 講師・生徒を並び替え
        self.fields['teacher'].queryset = Teacher.objects.order_by('name')
        self.fields['students'].queryset = Student.objects.order_by('child_name')

        # -----------------------------
        # ★ 開始時間・終了時間 初期値
        # -----------------------------
        # ● ① 更新モード（instanceあり）
        if self.instance.start_time:
            self.fields['start_hour'].initial = self.instance.start_time.strftime("%H")
            self.fields['start_minute'].initial = self._round_minute(self.instance.start_time.strftime("%M"))

        if self.instance.end_time:
            self.fields['end_hour'].initial = self.instance.end_time.strftime("%H")
            self.fields['end_minute'].initial = self._round_minute(self.instance.end_time.strftime("%M"))

        # ● ② 新規作成（get_initial() で initial に start_time がある）
        if "start_time" in self.initial:
            st = self.initial["start_time"]
            self.fields['start_hour'].initial = st.strftime("%H")
            self.fields['start_minute'].initial = self._round_minute(st.strftime("%M"))

        if "end_time" in self.initial:
            et = self.initial["end_time"]
            self.fields['end_hour'].initial = et.strftime("%H")
            self.fields['end_minute'].initial = self._round_minute(et.strftime("%M"))

    def _round_minute(self, minute):
        minute = int(minute)
        if minute < 15: return "00"
        elif minute < 30: return "15"
        elif minute < 45: return "30"
        else: return "45"

    def clean(self):
        cleaned_data = super().clean()

        from datetime import time
        cleaned_data["start_time"] = time(
            int(cleaned_data["start_hour"]),
            int(cleaned_data["start_minute"])
        )
        cleaned_data["end_time"] = time(
            int(cleaned_data["end_hour"]),
            int(cleaned_data["end_minute"])
        )

        if cleaned_data["start_time"] >= cleaned_data["end_time"]:
            self.add_error('end_hour', "終了時刻は開始時刻より後にしてください。")

        return cleaned_data
