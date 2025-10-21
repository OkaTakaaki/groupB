from django.shortcuts import render

#login
def login(request):
	return render(request, 'accounts/login.html')

#logout
def logout(request):
	return render(request, 'accounts/logout.html')

#guardian-create-account
def gcaccount(request):
	return render(request, 'accounts/gcaccount.html')

#teacher-create-account
def tcaccount(request):
	return render(request, 'accounts/tcaccounts.html')
