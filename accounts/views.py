from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from app.models import Student, Teacher, Parent
from django.contrib.auth.hashers import make_password, check_password
from django import forms
from PIL import Image
import qrcode, traceback, io, base64
from io import BytesIO
from django.core.files.base import ContentFile

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from app.models import Parent, Teacher, StudentAttendanceRule

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
                return redirect('app:student_parent_menu')

        # 講師ログイン
        teacher = Teacher.objects.filter(login_id=login_id).first()
        if teacher:
            if teacher.password_hash == password or check_password(password, teacher.password_hash):
                request.session['user_type'] = 'teacher'
                request.session['user_id'] = teacher.id
                messages.success(request, f"{teacher.name}先生、ログインしました。")
                return redirect('app:attendance_today')

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
    # -----------------------
    # 既存：保護者情報
    # -----------------------
    parent_login_id = forms.EmailField(label="保護者ログインID（メールアドレス）", required=True)
    parent_password = forms.CharField(label="保護者パスワード", widget=forms.PasswordInput, required=True)
    parent_name = forms.CharField(label="保護者氏名", required=True)
    parent_phone = forms.CharField(label="保護者電話番号", required=False)

    # -----------------------
    # ★ 追加：基本出席ルール
    # -----------------------
    DAYS = [
        ("Mon", "月"),
        ("Tue", "火"),
        ("Wed", "水"),
        ("Thu", "木"),
        ("Fri", "金"),
        ("Sat", "土"),
        ("Sun", "日"),
    ]

    attendance_days = forms.MultipleChoiceField(
        label="基本出席曜日",
        choices=DAYS,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    start_time = forms.TimeField(
        label="開始時刻",
        widget=forms.TimeInput(attrs={"type": "time"}),
        required=True
    )

    end_time = forms.TimeField(
        label="終了時刻",
        widget=forms.TimeInput(attrs={"type": "time"}),
        required=True
    )

    class Meta:
        model = Student
        fields = [
            'child_name',
            'child_name_kana',
            'user_type',
            'birth_date',
            'gender',
            'school_name',
            'address',
        ]

        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(),
        }

    # -----------------------
    # ★ 時刻バリデーション
    # -----------------------
    def clean(self):
        cleaned = super().clean()
        st = cleaned.get("start_time")
        et = cleaned.get("end_time")

        if st and et and st >= et:
            raise forms.ValidationError("終了時刻は開始時刻より後にしてください。")

        return cleaned


#student-create-account
def scaccount(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            try:
                # --------------------
                # 保護者作成（既存）
                # --------------------
                parent, created = Parent.objects.get_or_create(
                    login_id=form.cleaned_data['parent_login_id'],
                    defaults={
                        'password_hash': make_password(form.cleaned_data['parent_password']),
                        'name': form.cleaned_data['parent_name'],
                        'phone': form.cleaned_data.get('parent_phone', ''),
                    }
                )

                if created or not parent.qr_code:
                    qr_data = parent.login_id
                    qr_img = qrcode.make(qr_data)
                    buffer = BytesIO()
                    qr_img.save(buffer, format='PNG')
                    parent.qr_code.save(
                        f"{qr_data}.png",
                        ContentFile(buffer.getvalue()),
                        save=True
                    )

                # --------------------
                # 生徒作成（既存）
                # --------------------
                student = form.save(commit=False)
                student.parent = parent
                student.save()

                # =================================================
                # ★ ここから追加：出席ルール保存
                # =================================================
                days = form.cleaned_data["attendance_days"]
                start_time = form.cleaned_data["start_time"]
                end_time = form.cleaned_data["end_time"]

                for day in days:
                    StudentAttendanceRule.objects.create(
                        student=student,
                        day_of_week=day,
                        start_time=start_time,
                        end_time=end_time,
                    )

                # =================================================

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
            'login_id', 
            'name', 
            'name_kana',
            'birth_date',
            'gender', 
            'phone', 
            'permission_level'
        ]

        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(),
            'permission_level': forms.Select(),
        }

        labels = {
            'login_id': 'ログインID（メールアドレス）',
        }


class TeacherCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(),
        required=True
    )

    birth_date = forms.DateField(
        label="生年月日",
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d'],
        required=True
    )

    class Meta:
        model = Teacher
        fields = [
            'login_id', 
            'name', 
            'name_kana',
            'birth_date', 
            'gender', 
            'phone', 
            'permission_level'
        ]

def tcaccount(request):
    if request.method == 'POST':
        form = TeacherCreateForm(request.POST)
        if form.is_valid():
            teacher = form.save(commit=False)

            # ✅ 明示的に user_type をセット
            teacher.user_type = "teacher"

            # ✅ パスワードをハッシュ化
            teacher.password_hash = make_password(
                form.cleaned_data['password']
            )

            teacher.save()
            messages.success(request, '講師アカウントを作成しました。')
            return redirect('tcaccount')
        else:
            print(form.errors)
    else:
        form = TeacherCreateForm()

    return render(request, 'accounts/tcaccount.html', {'form': form})


#student-select
def student_select(request):
    if 'user_id' not in request.session:  # ← セッションにユーザー情報がなければ
        return redirect('login')          # ログイン画面へ飛ばす
    query = request.GET.get('q')
    if query:
        students = Student.objects.filter(id=query)
        parents = Parent.objects.filter(id=query)
    else:
        students = Student.objects.all().order_by('id')
        parents = Parent.objects.all().order_by('id')
    return render(request, 'accounts/sselect.html', {'students': students, 'parents': parents})

# student-edit-account
def seaccount(request, student_id):
    if 'user_id' not in request.session:
        return redirect('login')

    student = get_object_or_404(Student, id=student_id)
    parent = student.parent
    old_email = parent.login_id if parent else None

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save(commit=False)

            # --- Parent情報の更新 ---
            if parent:
                new_email = form.cleaned_data['parent_login_id']

                # メールアドレス変更
                email_changed = old_email != new_email
                parent.login_id = new_email
                parent.name = form.cleaned_data['parent_name']
                parent.phone = form.cleaned_data.get('parent_phone', '')

                # パスワードが入力されていれば更新
                if form.cleaned_data.get('parent_password'):
                    parent.password_hash = make_password(
                        form.cleaned_data['parent_password']
                    )

                # ★ メール変更時のみQRコード再生成
                if email_changed or not parent.qr_code:
                    qr_img = qrcode.make(new_email)
                    buffer = io.BytesIO()
                    qr_img.save(buffer, format='PNG')

                    filename = f"parent_qr_{new_email}.png"

                    parent.qr_code.save(
                        filename,
                        ContentFile(buffer.getvalue()),
                        save=True   # ← ここが重要
                    )

            student.save()
            messages.success(request, '生徒情報を更新しました。')
            return redirect('student_select')
        else:
            messages.error(request, '入力内容に誤りがあります。')
    else:
        form = StudentForm(instance=student)

    return render(request, 'accounts/seaccount.html', {
        'form': form,
        'parent': parent,
        'student': student
    })

#teacher-select
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

