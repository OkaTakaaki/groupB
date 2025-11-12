# forms.py
from django import forms
from .models import Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']  # ユーザーが入力するのは本文のみ
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'メッセージを入力'}),
        }
