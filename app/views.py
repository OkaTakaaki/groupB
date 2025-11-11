from django.shortcuts import render, redirect, get_object_or_404
from .models import User, Message
from .forms import MessageForm


# 初回アクセス時にゲストを自動追加
def create_guest_users():
    guest_names = ["ゲストA", "ゲストB", "ゲストC", "ゲストD"]
    for name in guest_names:
        User.objects.get_or_create(username=name)


def chat_view(request, user_id=None):
    # ゲストを自動登録
    create_guest_users()

    # 仮のログインユーザーを設定（本番では認証に置き換え可能）
    current_user, _ = User.objects.get_or_create(username="あなた")

    # 🔍 検索キーワードを取得
    query = request.GET.get("q")

    # 自分以外のユーザーを取得（検索機能対応）
    if query:
        users = User.objects.exclude(id=current_user.id).filter(username__icontains=query)
    else:
        users = User.objects.exclude(id=current_user.id)

    selected_user = None
    messages = []

    # チャット相手が指定されている場合
    if user_id:
        selected_user = get_object_or_404(User, id=user_id)
        messages = Message.objects.filter(
            sender__in=[current_user, selected_user],
            receiver__in=[current_user, selected_user]
        ).order_by('timestamp')

    # メッセージ送信処理
    if request.method == "POST" and selected_user:
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = current_user
            msg.receiver = selected_user
            msg.save()
            return redirect('chat', user_id=selected_user.id)
    else:
        form = MessageForm()

    context = {
        'users': users,
        'selected_user': selected_user,
        'messages': messages,
        'form': form,
        'current_user': current_user,
        'query': query or "",  # ← 入力欄に前回の検索ワードを残す
    }
    return render(request, 'app/chat.html', context)


def home_view(request):
    return render(request, 'app/home.html')


def user_list_view(request):
    users = User.objects.all()
    return render(request, 'app/users.html', {'users': users})


def message_list_view(request):
    messages = Message.objects.all().order_by('-timestamp')
    return render(request, 'app/messages.html', {'messages': messages})


def calendar_view(request):
    return render(request, 'app/calendar.html')


def settings_view(request):
    return render(request, 'app/settings.html')
