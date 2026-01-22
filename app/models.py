from django.db import models
from django.utils import timezone


# =========================
# 保護者
# =========================
class Parent(models.Model):
    login_id = models.EmailField(
        max_length=100, unique=True, verbose_name="ログインID(メールアドレス)"
    )
    qr_code = models.ImageField(
        upload_to='qr_codes/', blank=True, null=True, verbose_name="QRコード画像"
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

    def __str__(self):
        return self.name


# =========================
# 生徒
# =========================
class Student(models.Model):
    parent = models.ForeignKey(
        Parent, null=True, blank=True, on_delete=models.SET_NULL
    )

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
        return self.child_name

# =========================
# ★ 時間帯モデル
# =========================
class TimeSlot(models.Model):
    name = models.CharField("時間帯名", max_length=50)
    start_time = models.TimeField("開始時刻")
    end_time = models.TimeField("終了時刻")

    class Meta:
        db_table = "time_slots"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')})"

# =========================
# 出席記録
# =========================
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()

    time_slot = models.ForeignKey(   # ← 追加
        TimeSlot,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="時間帯"
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("present", "出席"),
            ("absent", "欠席"),
        ]
    )


# =========================
# ★ 基本出席ルール（曜日＋時間）
# =========================
class StudentAttendanceRule(models.Model):
    DAYS_OF_WEEK = [
        ('Mon', '月曜日'),
        ('Tue', '火曜日'),
        ('Wed', '水曜日'),
        ('Thu', '木曜日'),
        ('Fri', '金曜日'),
        ('Sat', '土曜日'),
        ('Sun', '日曜日'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_rules",
        verbose_name="生徒"
    )

    time_slot = models.ForeignKey(
    TimeSlot,
    on_delete=models.PROTECT,
    verbose_name="時間帯",
    null=True,
    blank=True
    )

    day_of_week = models.CharField(
        max_length=3,
        choices=DAYS_OF_WEEK,
        verbose_name="出席曜日"
    )

    class Meta:
        unique_together = ("student", "day_of_week")

    def __str__(self):
        return f"{self.student.child_name} {self.get_day_of_week_display()} {self.time_slot}"

# =========================
# 講師
# =========================
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


# =========================
# 授業スケジュール（振替・特別授業）
# =========================
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

    students = models.ManyToManyField(
        Student,
        verbose_name="生徒（複数）",
        related_name="schedules"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='予定',
        verbose_name="ステータス"
    )

    # 振替元の日付（必要なら将来使用）
    original_date = models.DateField(
        null=True, blank=True, verbose_name="振替元日"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "schedule"
        verbose_name = "授業スケジュール"
        verbose_name_plural = "授業スケジュール一覧"

    def __str__(self):
        student_names = ", ".join(s.child_name for s in self.students.all())
        return f"{self.date} {self.start_time}-{self.end_time} / {student_names} ({self.status})"

# =========================
# メッセージ（チャット）
# =========================
class Message(models.Model):
    parent_sender = models.ForeignKey(
        Parent, related_name='sent_messages',
        on_delete=models.CASCADE, blank=True, null=True
    )
    teacher_sender = models.ForeignKey(
        Teacher, related_name='sent_messages',
        on_delete=models.CASCADE, blank=True, null=True
    )

    parent_receiver = models.ForeignKey(
        Parent, related_name='received_messages',
        on_delete=models.CASCADE, blank=True, null=True
    )
    teacher_receiver = models.ForeignKey(
        Teacher, related_name='received_messages',
        on_delete=models.CASCADE, blank=True, null=True
    )

    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sender = self.parent_sender or self.teacher_sender
        receiver = self.parent_receiver or self.teacher_receiver
        return f"{sender} → {receiver}: {self.content[:20]}"


# =========================
# お知らせ
# =========================
class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    date = models.DateField(auto_now_add=True)
    sender = models.ForeignKey(Teacher, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title}（{self.date}）"
