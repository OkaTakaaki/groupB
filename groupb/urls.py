from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include

urlpatterns = [
    path('', lambda request: redirect('login')),
    path('admin/', admin.site.urls),
    path('app/', include('app.urls')),  # ← app側のurls.pyを読み込む
    path('accounts/', include('accounts.urls')),  # ← app側のurls.pyを読み込む
]
