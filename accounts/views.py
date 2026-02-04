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
from app.models import Parent, Teacher, StudentAttendanceRule, TimeSlot, TeacherAttendanceRule

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


from app.models import Student, TimeSlot   # ← TimeSlotをimport

class StudentForm(forms.ModelForm):

    # --- 保護者情報 ---
    parent_login_id = forms.EmailField(
        label="保護者ログインID（メールアドレス）",
        required=True
    )
    parent_password = forms.CharField(
        label="保護者パスワード",
        widget=forms.PasswordInput,
        required=True
    )
    parent_name = forms.CharField(
        label="保護者氏名",
        required=True
    )
    parent_phone = forms.CharField(
        label="保護者電話番号",
        required=False
    )

    # --- 曜日 ---
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
        label="出席曜日",
        choices=DAYS,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    # --- ✅ 時間帯マスタ選択 ---
    time_slot = forms.ModelChoiceField(
        label="出席時間帯",
        queryset=TimeSlot.objects.all().order_by("start_time"),
        empty_label="時間帯を選択してください",
        required=False
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


# ==============================
# 生徒アカウント作成
# ==============================
def scaccount(request):
    time_slots = TimeSlot.objects.all().order_by("start_time")
    print("利用可能な時間帯:", time_slots)

    if request.method == 'POST':
        form = StudentForm(request.POST)

        if form.is_valid():
            try:
                # 保護者作成
                parent, created = Parent.objects.get_or_create(
                    login_id=form.cleaned_data['parent_login_id'],
                    defaults={
                        'password_hash': make_password(form.cleaned_data['parent_password']),
                        'name': form.cleaned_data['parent_name'],
                        'phone': form.cleaned_data.get('parent_phone', ''),
                    }
                )

                # QRコード作成
                if created or not parent.qr_code:
                    qr_img = qrcode.make(parent.login_id)
                    buffer = BytesIO()
                    qr_img.save(buffer, format='PNG')
                    parent.qr_code.save(
                        f"{parent.login_id}.png",
                        ContentFile(buffer.getvalue()),
                        save=True
                    )

                # 生徒作成
                student = form.save(commit=False)
                student.parent = parent
                student.save()

                # 出席ルール保存
                selected_days = request.POST.getlist("attendance_days")
                print("選択された曜日:", selected_days)
                for day in selected_days:
                    time_slot_id = request.POST.get(f"time_slot_{day}")
                    if not time_slot_id:
                        continue
                    time_slot = TimeSlot.objects.get(id=time_slot_id)
                    StudentAttendanceRule.objects.create(
                        student=student,
                        day_of_week=day,
                        time_slot=time_slot,
                    )

                messages.success(request, f"生徒「{student.child_name}」を登録しました。")
                return redirect('scaccount')

            except Exception as e:
                print("登録エラー:", e)
                messages.error(request, "登録中にエラーが発生しました。")
        else:
            print("フォームエラー:", form.errors)   
            messages.error(request, "入力内容に誤りがあります。")

    else:
        form = StudentForm()

    # ✅ scaccount は新規作成なので day_times は空
    day_times = {}

    return render(request, 'accounts/scaccount.html', {
        'form': form,
        'time_slots': time_slots,
        'day_times': day_times,
    })


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
    time_slots = TimeSlot.objects.all().order_by("start_time")

    week_days = [
        ('Mon', '月'),
        ('Tue', '火'),
        ('Wed', '水'),
        ('Thu', '木'),
        ('Fri', '金'),
        ('Sat', '土'),
        ('Sun', '日'),
    ]

    if request.method == 'POST':
        form = TeacherCreateForm(request.POST)
        if form.is_valid():
            teacher = form.save(commit=False)
            teacher.user_type = "teacher"
            teacher.password_hash = make_password(
                form.cleaned_data['password']
            )
            teacher.save()

            # ★ 基本勤務ルール保存
            selected_days = request.POST.getlist("attendance_days")
            for day in selected_days:
                time_slot_id = request.POST.get(f"time_slot_{day}")
                if not time_slot_id:
                    continue
                TeacherAttendanceRule.objects.create(
                    teacher=teacher,
                    day_of_week=day,
                    time_slot_id=time_slot_id,
                )

            messages.success(request, '講師アカウントを作成しました。')
            return redirect('tcaccount')
    else:
        form = TeacherCreateForm()

    return render(request, 'accounts/tcaccount.html', {
        'form': form,
        'time_slots': time_slots,
        'week_days': week_days,  # ← ★ これ
    })


#student-select
from django.shortcuts import render, redirect
from django.contrib import messages

def student_select(request):
    # ログインチェック
    if 'user_id' not in request.session:
        return redirect('login')

    query = request.GET.get('q')
    students = Student.objects.none()
    parents = Parent.objects.none()

    try:
        if query:
            # 数字チェック（ID検索の安全化）
            if not query.isdigit():
                messages.warning(request, "検索IDは数字で入力してください。")
            else:
                students = Student.objects.filter(id=int(query))
                parents = Parent.objects.filter(id=int(query))

                # 該当なし
                if not students.exists() and not parents.exists():
                    messages.info(request, "該当するデータが見つかりませんでした。")
        else:
            students = Student.objects.all().order_by('id')
            parents = Parent.objects.all().order_by('id')

    except Exception as e:
        # 想定外エラー
        print("student_select error:", e)
        messages.error(request, "データの取得中にエラーが発生しました。")

        # フォールバック（空表示）
        students = Student.objects.none()
        parents = Parent.objects.none()

    return render(
        request,
        'accounts/sselect.html',
        {
            'students': students,
            'parents': parents,
        }
    )


# student-edit-account
def seaccount(request, student_id):
    if 'user_id' not in request.session:
        return redirect('login')

    student = get_object_or_404(Student, id=student_id)
    parent = student.parent
    old_email = parent.login_id if parent else None
    
    # 全時間帯のリスト（セレクトボックス用）
    time_slots = TimeSlot.objects.all().order_by("start_time")

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            # ... (中略：現在の保護者更新・QRコード処理) ...
            
            student.save()
            
            # ★ 出席ルールの更新処理を追加
            selected_days = request.POST.getlist('attendance_days')
            # 一旦、今のルールを削除して再登録（または更新）
            student.attendance_rules.all().delete()
            for day in selected_days:
                slot_id = request.POST.get(f'{day}_time_slot') # テンプレートのname属性に合わせる
                if slot_id:
                    slot = TimeSlot.objects.get(id=slot_id)
                    StudentAttendanceRule.objects.create(
                        student=student,
                        day_of_week=day,
                        time_slot=slot
                    )

            messages.success(request, '生徒情報を更新しました。')
            return redirect('student_select')
    else:
        # 初期表示のとき：保護者の情報をフォームに詰める
        initial_data = {}
        if parent:
            initial_data = {
                'parent_login_id': parent.login_id,
                'parent_name': parent.name,
                'parent_phone': parent.phone,
            }
        form = StudentForm(instance=student, initial=initial_data)

    # ★ テンプレートでの表示用にデータを整理する
    # 現在のルールを { 'Mon': ID, 'Tue': ID } という辞書にする
    current_rules = student.attendance_rules.all()
    selected_days = [r.day_of_week for r in current_rules]
    
    # テンプレートで引数付き辞書が使えない問題を回避するため
    # day_times をそのまま渡さず、あえて「そのままアクセスできる形」に工夫するか
    # 辞書を get フィルタで引けるように準備します。
    day_times = {r.day_of_week: r.time_slot.id for r in current_rules}

    return render(request, 'accounts/seaccount.html', {
        'form': form,
        'parent': parent,
        'student': student,
        'time_slots': time_slots,      
        'selected_days': selected_days, 
        'day_times': day_times,         
    })
#teacher-select
from django.shortcuts import render, redirect
from django.contrib import messages

def teacher_select(request):
    # ログインチェック
    if 'user_id' not in request.session:
        return redirect('login')

    query = request.GET.get('q')
    teachers = Teacher.objects.none()

    try:
        if query:
            # 数字チェック（ID検索の安全化）
            if not query.isdigit():
                messages.warning(request, "検索IDは数字で入力してください。")
            else:
                teachers = Teacher.objects.filter(id=int(query))

                # 該当データなし
                if not teachers.exists():
                    messages.info(request, "該当する教師データが見つかりませんでした。")
        else:
            teachers = Teacher.objects.all().order_by('id')

    except Exception as e:
        print("teacher_select error:", e)
        messages.error(request, "データ取得中にエラーが発生しました。")
        teachers = Teacher.objects.none()

    return render(
        request,
        'accounts/tselect.html',
        {
            'teachers': teachers,
        }
    )

# teacher-edit-account
def teaccount(request, teacher_id):
    if 'user_id' not in request.session:
        return redirect('login')

    teacher = get_object_or_404(Teacher, id=teacher_id)
    time_slots = TimeSlot.objects.all().order_by("start_time")

    # 既存ルール取得
    rules = teacher.attendance_rules.all()
    selected_days = [r.day_of_week for r in rules]

    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)

        if form.is_valid():
            form.save()

            # ===== 勤務ルールを一旦削除 =====
            TeacherAttendanceRule.objects.filter(teacher=teacher).delete()

            # ===== 再登録 =====
            selected_days = request.POST.getlist("attendance_days")

            for day in selected_days:
                time_slot_id = request.POST.get(f"{day}_time_slot")
                if not time_slot_id:
                    continue

                TeacherAttendanceRule.objects.create(
                    teacher=teacher,
                    day_of_week=day,
                    time_slot_id=time_slot_id,
                    is_primary=True
                )

            messages.success(request, "講師情報を更新しました。")
            return redirect('teacher_select')

        else:
            messages.error(request, "入力内容に誤りがあります。")

    else:
        form = TeacherForm(instance=teacher)

    return render(request, 'accounts/teaccount.html', {
        'form': form,
        'teacher': teacher,
        'time_slots': time_slots,
        'selected_days': selected_days,
    })


class TimeSlotForm(forms.ModelForm):
    class Meta:
        model = TimeSlot
        fields = ['name', 'start_time', 'end_time']
        labels = {
            'name': '時間帯名',
            'start_time': '開始時刻',
            'end_time': '終了時刻',
        }
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')

        if start and end and start >= end:
            raise forms.ValidationError("開始時刻は終了時刻より前にしてください。")

def timeslot_edit(request, pk):
    slot = get_object_or_404(TimeSlot, pk=pk)

    if request.method == 'POST':
        form = TimeSlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            return redirect('app:timeslot_list')
    else:
        form = TimeSlotForm(instance=slot)

    return render(request, 'app/timeslot_edit.html', {
        'form': form,
        'slot': slot
    })

