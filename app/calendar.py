from calendar import HTMLCalendar
from datetime import date
from django.urls import reverse

class CustomCalendar(HTMLCalendar):
    """
    指定された年/月の月間カレンダーを生成し、イベントを表示するためのカスタムクラスです。
    """
    def __init__(self, year=None, month=None, events=None):
        super().__init__()
        self.year = year
        self.month = month
        self.events = events or []

    def formatday(self, day, weekday):
        """
        カレンダーの各日セルをHTMLとしてフォーマットします。
        
        :param day: 月の日 (1-31) または当月以外の場合は 0。
        :param weekday: 曜日の番号 (0=月曜, 6=日曜)。
        :return: <td>タグを含むHTML文字列。
        """
        
        if day == 0:
            # 当月以外の日には空のセルを返します
            return '<td class="noday">&nbsp;</td>'

        # カレンダー上の特定の日付を確定します
        cal_date = date(self.year, self.month, day)
        # 曜日に基づくCSSクラスを取得します
        css_class = self.cssclasses[weekday]
        # 今日であれば 'today' クラスを追加します
        if cal_date == date.today():
            css_class += ' today'
        
        # この特定の日付に重複するイベントをフィルタリングします
        day_events = [
            event for event in self.events 
            if event.start_time.date() <= cal_date and event.end_time.date() >= cal_date
        ]
        
        events_html = '<ul class="event-list">'
        for event in day_events:
            # イベント編集URLを生成します
            event_edit_url = reverse('app:event_update', kwargs={'pk': event.pk})
            title = f"{event.title}"
            
            # イベントへのリンクを作成します
            events_html += f'<li><a href="{event_edit_url}" class="event-link">{title}</a></li>'
        events_html += '</ul>'

        # 日間カレンダービューへのURLを生成します
        daily_url = reverse('app:calendar_day', kwargs={'year': self.year, 'month': self.month, 'day': day})
        
        # セル内のコンテンツを構築します
        content = (
            f'<div class="day-wrapper">'
            f'<a href="{daily_url}" class="date-number-link">' 
            f'<div class="date-number">{day}</div>'
            f'</a>'
            f'{events_html}'
            f'</div>'
        )

        # 最終的な<td>要素を返します
        return f'<td class="{css_class} calendar-day" data-date="{cal_date}">{content}</td>'

    def formatweek(self, theweek):
        # よりクリーンなHTML出力のために不要な改行を削除します
        week_html = super().formatweek(theweek)
        return week_html.replace('>\n<', '><')

    def formatmonth(self, theyear, themonth, withyear=True):
        # 修正: 親クラスのメソッドを呼び出す際に、引数として渡されたtheyearとthemonthを使用します。
        # 親クラスのメソッドがformatdayを呼び出す際、その日と曜日以外の情報は使いません。
        calendar_html = super().formatmonth(theyear, themonth)
        
        # カスタムスタイリングのためにデフォルトのテーブルクラスを置換します
        calendar_html = calendar_html.replace('<table border="0" cellpadding="0" cellspacing="0" class="month">', 
                                              '<table border="0" cellpadding="0" cellspacing="0" class="calendar">', 1)
        return calendar_html

    def formatweekday(self, day):
        # 日本語の曜日の名前を使用します
        weekday_names_ja = ['月', '火', '水', '木', '金', '土', '日']
        return f'<th class="{self.cssclasses[day]}">{weekday_names_ja[day]}</th>'

    def formatmonthname(self, theyear, themonth, withyear=True):
        # 月の名前はテンプレート側で処理するため、空を返します
        return ''