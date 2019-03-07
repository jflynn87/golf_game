from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, FormView
from golf_app.models import Tournament
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateResponseMixin
from django.urls import reverse, reverse_lazy
from django.contrib.auth.models import User
from base_app.forms import UserForm


def user_login(request):

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username,password=password)

        if user:
            if user.is_active:
                login(request, user)
                #return HttpResponseRedirect(reverse('index'))
                return render (request, 'index.html', {}
                )
            else:
                return HttpResponse("Your account is not active")
        else:
            print ("someone tried to log in and failed")
            #print ("Username: {} and password {}".format(username,password))
            print ("Username: {} ".format(username))
            return HttpResponse("invalid login details supplied")
    else:
        return render(request, 'login.html', {})


def index(request):
    print ('first here')
    if request.method == "GET":
        return render(request, 'index.html', {
                })

        #return render(request, 'index.html', {
        #'tournament': Tournament.objects.get(current=True),
        #})


@login_required
def special(request):
    return HttpResponse("You are logged in!")


def register(request):
    registered = False

    if request.method == "POST":
        user_form = UserForm(data=request.POST)


        if user_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()

            registered = True
        else:
            print(user_form.errors)

    else:
        user_form = UserForm()


    return render(request,'registration.html',
                            {'user_form': user_form,
                             'registered': registered})


@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))
