from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader


def home(request):
    template = loader.get_template("app/home.html")
    return HttpResponse(template.render({}, request))

# Create your views here.
