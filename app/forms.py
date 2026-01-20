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
        fields = ['date', 'teacher', 'students', 'status']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
            'teacher': forms.Select(attrs={'class': 'form-input'}),
            'students': forms.SelectMultiple(attrs={'class': 'form-input', 'size': 6}),
            'status': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['teacher'].queryset = Teacher.objects.order_by('name')
        self.fields['students'].queryset = Student.objects.order_by('child_name')

        if self.instance and self.instance.start_time:
            self.fields['start_hour'].initial = self.instance.start_time.strftime("%H")
            self.fields['start_minute'].initial = self._round_minute(
                self.instance.start_time.strftime("%M")
            )

        if self.instance and self.instance.end_time:
            self.fields['end_hour'].initial = self.instance.end_time.strftime("%H")
            self.fields['end_minute'].initial = self._round_minute(
                self.instance.end_time.strftime("%M")
            )

    def _round_minute(self, minute):
        minute = int(minute)
        if minute < 15: return "00"
        elif minute < 30: return "15"
        elif minute < 45: return "30"
        else: return "45"

    def clean(self):
        cleaned_data = super().clean()
        from datetime import time

        sh = cleaned_data.get("start_hour")
        sm = cleaned_data.get("start_minute")
        eh = cleaned_data.get("end_hour")
        em = cleaned_data.get("end_minute")

        if not all([sh, sm, eh, em]):
            return cleaned_data

        cleaned_data["start_time"] = time(int(sh), int(sm))
        cleaned_data["end_time"] = time(int(eh), int(em))

        if cleaned_data["start_time"] >= cleaned_data["end_time"]:
            self.add_error('end_hour', "終了時刻は開始時刻より後にしてください。")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.start_time = self.cleaned_data["start_time"]
        instance.end_time = self.cleaned_data["end_time"]

        if commit:
            instance.save()
            self.save_m2m()

        return instance
