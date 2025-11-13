from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader


def smenu_view(request):
    template = loader.get_template("app/smenu.html")
    return HttpResponse(template.render({}, request))