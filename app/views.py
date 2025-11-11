from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader

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

#メール
def mail_list(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    return render(request, 'mail_list.html')

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


