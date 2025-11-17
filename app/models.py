from django.db import models
 
#保護者
class Parent(models.Model):
    login_id = models.EmailField(
        max_length=100, unique=True, verbose_name="ログインID(メールアドレス)"
    )
    user_type = models.CharField(
        max_length=10, default='parent', verbose_name="ユーザータイプ"
    )
    password_hash = models.CharField(
        max_length=255, verbose_name="パスワード（ハッシュ）"
    )
    name = models.CharField(
        max_length=100, verbose_name="親氏名"
    )
    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="電話番号"
    )
 
#生徒
class Student(models.Model):
    parent = models.ForeignKey(Parent, null=True, blank=True, on_delete=models.SET_NULL)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    GENDER_CHOICES = [
        ('男', '男'),
        ('女', '女'),
        ('その他', 'その他'),
    ]
 
    user_type = models.CharField(
        max_length=10, default='student', verbose_name="ユーザータイプ"
    )
    child_name = models.CharField(
        max_length=100, verbose_name="子ども氏名"
    )
    child_name_kana = models.CharField(
        max_length=100, verbose_name="子ども氏名（かな）"
    )
    birth_date = models.DateField(
        verbose_name="生年月日"
    )
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, verbose_name="性別"
    )
    school_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="学校名"
    )
    address = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="住所"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="登録日時"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="更新日時"
    )
 
    class Meta:
        db_table = 'students'
        verbose_name = "生徒"
        verbose_name_plural = "生徒一覧"
 
    def __str__(self):
        return f"{self.child_name} parent: {self.parent.name}"
 
#講師
class Teacher(models.Model):
    user_type = models.CharField(
        max_length=10, default='teacher', verbose_name="ユーザータイプ"
    )
    GENDER_CHOICES = [
        ('男', '男'),
        ('女', '女'),
        ('その他', 'その他'),
    ]
 
    PERMISSION_CHOICES = [
        ('一般講師', '一般講師'),
        ('主任講師', '主任講師'),
        ('管理者', '管理者'),
    ]
 
    login_id = models.EmailField(
        max_length=100, unique=True, verbose_name="ログインID"
    )
    password_hash = models.CharField(
        max_length=255, verbose_name="パスワード（ハッシュ）"
    )
    name = models.CharField(
        max_length=100, verbose_name="氏名"
    )
    name_kana = models.CharField(
        max_length=100, verbose_name="氏名（かな）"
    )
    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="電話番号"
    )
    birth_date = models.DateField(
        verbose_name="生年月日"
    )
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, verbose_name="性別"
    )
    permission_level = models.CharField(
        max_length=10, choices=PERMISSION_CHOICES, verbose_name="権限"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="登録日時"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="更新日時"
    )
 
    class Meta:
        db_table = 'teachers'
        verbose_name = "講師"
        verbose_name_plural = "講師一覧"
 
    def __str__(self):
        return f"{self.name} ({self.permission_level})"
 
#スケジュール
class Schedule(models.Model):
    STATUS_CHOICES = [
        ('予定', '予定'),
        ('出席', '出席'),
        ('欠席', '欠席'),
        ('振替', '振替'),
        ('中止', '中止'),
    ]
 
    date = models.DateField(verbose_name="授業日")
    start_time = models.TimeField(verbose_name="開始時刻")
    end_time = models.TimeField(verbose_name="終了時刻")
 
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        verbose_name="担当講師",
        related_name="schedules"
    )
 
    # ★★★ 変更①：生徒を複数選択できるように ManyToManyField に変更 ★★★
    # ★★★ 変更②：ManyToManyField には on_delete は書かないので削除 ★★★
    students = models.ManyToManyField(
        Student,
        verbose_name="生徒（複数）",      # ← 表示名も複数に変更
        related_name="schedules"
    )
 
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='予定',
        verbose_name="ステータス"
    )
 
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
 
    class Meta:
        db_table = "schedule"
        verbose_name = "授業スケジュール"
        verbose_name_plural = "授業スケジュール一覧"
 
    # ★★★ 変更③：複数生徒の名前をカンマ区切りで表示できるように修正 ★★★
    def __str__(self):
        student_names = ", ".join(s.child_name for s in self.students.all())
        return f"{self.date} {self.start_time}-{self.end_time} / {self.teacher} -> {student_names}"

# メッセージ
class Message(models.Model):
    # 送信者
    student_sender = models.ForeignKey(
        Student, related_name='sent_messages', on_delete=models.CASCADE, blank=True, null=True
    )
    teacher_sender = models.ForeignKey(
        Teacher, related_name='sent_messages', on_delete=models.CASCADE, blank=True, null=True
    )
 
    # 受信者
    student_receiver = models.ForeignKey(
        Student, related_name='received_messages', on_delete=models.CASCADE, blank=True, null=True
    )
    teacher_receiver = models.ForeignKey(
        Teacher, related_name='received_messages', on_delete=models.CASCADE, blank=True, null=True
    )
 
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        sender = self.student_sender or self.teacher_sender
        receiver = self.student_receiver or self.teacher_receiver
        return f"{sender} → {receiver}: {self.content[:20]}"