from django import template

register = template.Library()


@register.filter
def get_day_of_week(date_obj):
    """
    0:日, 1:月, ... 6:土 の曜日番号を返す。
    Django weekday(): 月=0〜日=6 を変換。
    """
    return (date_obj.weekday() + 1) % 7


@register.filter
def get_item(dictionary, key):
    """辞書からキーの値を取得する。"""
    if dictionary is None:
        return None
    try:
        return dictionary.get(key)
    except AttributeError:
        return None


# ★★★★★ ここを追加（既存） ★★★★★
@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Djangoフォームのフィールドに class を付与するフィルタ
    使用例: {{ form.field|add_class:"form-control" }}
    """
    return field.as_widget(attrs={"class": css_class})
# ★★★★★ 追加ここまで ★★★★★


@register.filter
def to_int(value):
    """
    文字列を整数に変換するフィルター
    使用例: {{ "3"|to_int }}
    """
    try:
        return int(value)
    except:
        return 0


# ★ 追加：時刻を分へ変換（高さ計算用）
@register.filter
def time_to_minutes(time_obj):
    """ 時刻（time）→ 0〜1440 の分に変換 """
    return time_obj.hour * 60 + time_obj.minute

# 減算
@register.filter(name='minus')
def minus(value, arg):
    return int(value) - int(arg)

# 割り算（必要な場合）
@register.filter(name='div')
def div(value, arg):
    return int(value) / int(arg)


# ★★★ 追加：range を生成するフィルタ ★★★
@register.filter
def times(number):
    """
    指定した数だけ 0 からの連番リストを返す
    例: {{ 24|times }} → 0〜23
    """
    return range(number)


@register.filter
def mul(value, arg):
    """掛け算フィルター"""
    return int(value) * int(arg)


