from django.shortcuts import render, redirect, get_object_or_404
from .models import Student, Parent, Teacher, Message
from .forms import MessageForm
from django.http import HttpResponse
from django.template import loader
from django.db.models import Q

#ホーム
def home(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    return render(request, 'home.html')

#生徒
def student_information(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')  # ログイン画面へ飛ばす
    return render(request, 'student_information.html')

#カレンダー
def calendar(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    return render(request, 'calendar.html')

#設定
def setting(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    return render(request, 'setting.html')

#チャット

def mail_list(request, user_type=None, user_id=None):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす

    # ログインユーザー情報取得
    current_type = request.session['user_type']
    current_id = request.session['user_id']
    print(f"あああああああああああああああ{current_type}あああああああああああああああ")

    print(f"current_id---------------------{current_id}------------------------")

    if current_type == 'student'or current_type == 'parent':
        print(f"=====================student============================")
        print(f"====================={current_id}============================")
        current_user = get_object_or_404(Student, id=current_id)
        print(f"====================={current_user}============================")
    else:
        print(f"=====================teacher============================")
        print(f"====================={current_id}============================")
        current_user = get_object_or_404(Teacher, id=current_id)
        print(f"====================={current_user}============================")

    # チャット相手
    selected_user = None
    messages = []

    if user_id:  # user_type は不要
        if current_type == 'student' or current_type == 'parent':
            current_user = get_object_or_404(Student, id=current_id)
            if user_id:
                selected_user = get_object_or_404(Teacher, id=user_id)
                print(f"=====================student============================")
                print(f"====================={selected_user}============================")
        elif current_type == 'teacher':
            current_user = get_object_or_404(Teacher, id=current_id)
            if user_id:
                selected_user = get_object_or_404(Student, id=user_id)
                print(f"=======================teacher==========================")
                print(f"====================={selected_user}============================")
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

    print(f"あああああああああああああああ{current_type}あああああああああああああああ")
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
            return redirect('mail_detail', user_id=user_id)

    else:
        form = MessageForm()

    # ユーザー一覧（チャット可能な相手）
    print(f"current_type: {current_type!r}")  # !r でクオート付きの表示
    if current_type == "parent":
        print(f"<<<<<<<<<<<<<<parent>>>>>>>>>>>>>>")
    else:
        print(f"<<<<<<<<<<<<<<NO>>>>>>>>>>>>>>")

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