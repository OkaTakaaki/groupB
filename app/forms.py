from django import forms
from django.forms import DateInput
from .models import Schedule, Teacher, Message, TimeSlot

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'メッセージを入力'}),
        }


class ScheduleForm(forms.ModelForm):
    # ✅ モデルに無いけどフォーム上で選ばせる「時間帯」
    time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.none(),
        empty_label="時間帯を選択してください",
        label="時間帯",
        required=True
    )

    class Meta:
        model = Schedule
        fields = ['date', 'title', 'teacher']  # 3項目 + time_slotは上で追加
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
            'title': forms.TextInput(attrs={'placeholder': '授業予定'}),
            'teacher': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['teacher'].queryset = Teacher.objects.order_by('name')
        self.fields['time_slot'].queryset = TimeSlot.objects.all().order_by('start_time')

        # ✅ 編集時：start_time/end_time に一致する TimeSlot を初期選択にする
        if self.instance and self.instance.pk and self.instance.start_time and self.instance.end_time:
            slot = TimeSlot.objects.filter(
                start_time=self.instance.start_time,
                end_time=self.instance.end_time
            ).first()
            if slot:
                self.fields['time_slot'].initial = slot

        # ✅ 新規作成時：?slot_id= を受け取って初期選択
        # （CreateView側で initial を入れる方法もあるけど、フォームだけでも動くようにしておく）
        request = getattr(self, 'request', None)  # 通常は無いので後述の方法が確実
        # ↑ここは何もしない（下のviews版が確実）

    def clean(self):
        cleaned_data = super().clean()

        slot = cleaned_data.get("time_slot")
        if not slot:
            return cleaned_data

        # ✅ TimeSlotから開始/終了を決定
        cleaned_data["start_time"] = slot.start_time
        cleaned_data["end_time"] = slot.end_time

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # ✅ cleanで入れた時間を保存
        instance.start_time = self.cleaned_data["start_time"]
        instance.end_time = self.cleaned_data["end_time"]

        # ✅ 画面に出さないので固定
        instance.status = "予定"

        if commit:
            instance.save()
        return instance
