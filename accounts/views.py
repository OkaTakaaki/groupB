from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from app.models import Student, Teacher, Parent
from django.contrib.auth.hashers import make_password, check_password
from django import forms
from PIL import Image
import qrcode, traceback, io, base64
from io import BytesIO
from django.core.files.base import ContentFile

#login
def login(request):
    if request.method == "POST":
        login_id = request.POST.get("login_id")
        password = request.POST.get("password")

        # 保護者ログイン
        parent = Parent.objects.filter(login_id=login_id).first()
        if parent:
            if parent.password_hash == password or check_password(password, parent.password_hash):
                request.session['user_type'] = 'parent'
                request.session['user_id'] = parent.id
                messages.success(request, f"{parent.name}さん、ログインしました。")
                return redirect('home')

        # 講師ログイン
        teacher = Teacher.objects.filter(login_id=login_id).first()
        if teacher:
            if teacher.password_hash == password or check_password(password, teacher.password_hash):
                request.session['user_type'] = 'teacher'
                request.session['user_id'] = teacher.id
                messages.success(request, f"{teacher.name}先生、ログインしました。")
                return redirect('home')

        messages.error(request, "メールアドレスまたはパスワードが正しくありません。")

    return render(request, 'accounts/login.html')


#logout
def logout(request):
    """ログアウト処理"""
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    request.session.flush()
    messages.success(request, "ログアウトしました。")
    return redirect('login')


class StudentForm(forms.ModelForm):
    # 保護者情報も一緒に入力できるよう追加
    parent_login_id = forms.EmailField(label="保護者ログインID（メールアドレス）", required=True)
    parent_password = forms.CharField(label="保護者パスワード", widget=forms.PasswordInput, required=True)
    parent_name = forms.CharField(label="保護者氏名", required=True)
    parent_phone = forms.CharField(label="保護者電話番号", required=False)

    class Meta:
        model = Student
        fields = [
            'child_name', 'child_name_kana', 'user_type',
            'birth_date', 'gender', 'school_name', 'address'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(),
        }


#student-create-account
def scaccount(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            try:
                # 保護者を作成または取得（パスワードをハッシュ化して保存）
                parent, created = Parent.objects.get_or_create(
                    login_id=form.cleaned_data['parent_login_id'],
                    defaults={
                        'password_hash': make_password(form.cleaned_data['parent_password']),
                        'name': form.cleaned_data['parent_name'],
                        'phone': form.cleaned_data.get('parent_phone', ''),
                    }
                )
                qr_data = form.cleaned_data['parent_login_id']
                qr_img = qrcode.make(qr_data)
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                student = form.save(commit=False)
                student.parent = parent
                student.qr_code.save(f"{qr_data}.png", ContentFile(buffer.getvalue()))
                student.save()

                messages.success(request, f"生徒「{student.child_name}」を登録しました。")
                return redirect('scaccount')

            except Exception as e:
                print("登録エラー:", e)
                print(traceback.format_exc())
                messages.error(request, "登録中にエラーが発生しました。")

        else:
            messages.error(request, "入力内容に誤りがあります。")
    else:
        form = StudentForm()

    return render(request, 'accounts/scaccount.html', {'form': form})

#teacher-create-account
class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = [
            'login_id', 'name','name_kana', 'password_hash', 'birth_date',
            'gender', 'phone', 'permission_level'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(),
            'permission_level': forms.Select(),
        }
        labels = {
            'login_id': 'ログインID（メールアドレス）',
        }

def tcaccount(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            teacher = form.save(commit=False)
            # 入力されたパスワードをハッシュ化
            teacher.password_hash = make_password(form.cleaned_data['password_hash'])
            teacher.save()
            messages.success(request, '講師アカウントを作成しました。')
            return redirect('tcaccount')
        else:
            print(form.errors)
    else:
        form = TeacherForm()
    return render(request, 'accounts/tcaccount.html', {'form': form})

#student-select
def student_select(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    query = request.GET.get('q')
    if query:
        students = Student.objects.filter(id=query)
    else:
        students = Student.objects.all().order_by('id')
    return render(request, 'accounts/sselect.html', {'students': students})

#student-edit-account
def seaccount(request, student_id):
    if 'user_id' not in request.session:
        return redirect('login')
    
    student = get_object_or_404(Student, id=student_id)
    old_email = student.parent.login_id if student.parent else None

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save(commit=False)
            
            # Parent のメールアドレス変更があった場合
            if student.parent and old_email != student.parent.login_id:
                # QRコードを生成
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(student.parent.login_id)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")

                # メモリ上で保存
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                student.qr_code.save(f"qr_{student.id}.png", ContentFile(buffer.getvalue()), save=False)

            student.save()
            messages.success(request, '生徒情報を更新しました。')
            return redirect('seaccount', student_id=student.id)
        else:
            messages.error(request, '入力内容に誤りがあります。')
    else:
        form = StudentForm(instance=student)

    return render(request, 'accounts/seaccount.html', {'form': form, 'student': student})

def teacher_select(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    query = request.GET.get('q')
    if query:
        teachers = Teacher.objects.filter(id=query)
    else:
        teachers = Teacher.objects.all().order_by('id')
    return render(request, 'accounts/tselect.html', {'teachers': teachers})

def teaccount(request, teacher_id):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    teacher = get_object_or_404(Teacher, id=teacher_id)

    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, '講師情報を更新しました。')
            return redirect('teacher_select')
        else:
            messages.error(request, '入力内容に誤りがあります。')
    else:
        form = TeacherForm(instance=teacher)

    return render(request, 'accounts/teaccount.html', {'form': form, 'teacher': teacher})

