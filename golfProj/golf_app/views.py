from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, FormView
from golf_app.models import Field, Tournament, Picks, Group, TotalScore, ScoreDetails
#from golf_app.forms import  CreatePicksForm, PickFormSet, NoPickFormSet
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateResponseMixin
from django.urls import reverse, reverse_lazy
from django.contrib.auth.models import User
import datetime
from golf_app import populateField, calc_score, optimal_picks
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Min, Q, Count
import scipy.stats as ss
from django.http import JsonResponse
import json
import random


class FieldListView(LoginRequiredMixin,ListView):
    login_url = 'login'
    template_name = 'golf_app/field_list.html'
    model = Field
    redirect_field_name = 'golf_app/picks_list.html'

    def get_context_data(self,**kwargs):
        context = super(FieldListView, self).get_context_data(**kwargs)
        tournament = Tournament.objects.get(current=True)

        #check for withdrawls and create msg if there is any
        try:
            score_file = calc_score.getRanks({'pk': tournament.pk})
            wd_list = []
            for golfer in Field.objects.filter(tournament=tournament):
                if golfer.playerName not in score_file[0]:
                    print ('debug')
                    wd_list.append(golfer.playerName)
                    print ('wd list', wd_list)
            if len(wd_list) > 0:
                error_message = 'Caution, the following golfers have withdrawn:' + str(wd_list)
            else:
                error_message = None
        except Exception as e:
            print ('score file lookup issue', e)
            error_message = None

        context.update({
        'field_list': Field.objects.filter(tournament=Tournament.objects.get(current=True)),
        'tournament': tournament,
        'error_message': error_message
        })
        return context


    def post(self, request):
        tournament = Tournament.objects.get(current=True)
        group = Group.objects.filter(tournament=tournament)
        user = User.objects.get(username=request.user)
        print ('user', user)

        random_picks = []
        picks_list = []

        if datetime.date.today() >= tournament.start_date:
            print (tournament.start_date)
            print (timezone.now())
            return HttpResponse ("Sorry it is too late to submit picks.")

        if request.POST.get('random') == 'random':
            for g in group:
                random_picks.append(random.choice(Field.objects.filter(tournament=tournament, group=g)))
            print ('random picks', random_picks)
        else:
            form = request.POST
            picks = []
            for key, pick in form.items():
                if key not in  ('csrfmiddlewaretoken', 'userid'):
                    picks_list.append(pick)
            print (picks_list)

        if Picks.objects.filter(playerName__tournament__current=True, user=user).count()>0:
            Picks.objects.filter(playerName__tournament__current=True, user=user).delete()

        if request.POST.get('random'):
            for picks in random_picks:
                pick = Picks()
                pick.user = user
                pick.playerName = Field.objects.get(playerName=picks, tournament=tournament)
                pick.save()
        else:
            print (len(form), len(group))
            if (len(form)-2) == len(group):
                for k, v in form.items():
                   if k != 'csrfmiddlewaretoken' and k!= 'userid':
                       picks = Picks()
                       picks.user = User.objects.get(pk=form['userid'])
                       picks.playerName = Field.objects.get(pk=v)
                       picks.save()
            else:
                group_list = []
                for key, value in form.items():
                    if key not in ('userid', 'csrfmiddlewaretoken'):
                        group_list.append(key.split('-')[0])
                missing_group = []
                for num in group:
                    if str(num.number) not in group_list:
                        missing_group.append(num.number)
                print (request.user, 'picks missing group', missing_group)


                print (datetime.datetime.now(), request.user, form)
                return render (request, 'golf_app/field_list.html',
                    {'field_list': Field.objects.filter(tournament=tournament),
                     #'picks_list': Picks.objects.filter(playerName__tournament__current=True, user=form['userid']),
                     'form':form,
                     'picks': picks,
                     'tournament': Tournament.objects.get(current=True),
                     'error_message':  "Missing Picks for the following groups: " + str(missing_group),
                         })

        print ('submitting picks', datetime.datetime.now(), request.user, picks_list, 'random:', random_picks)
        return redirect('golf_app:picks_list')


def get_picks(request):
    if request.is_ajax():
        print (request.user)
        pick_list = []
        for pick in Picks.objects.filter(user__username=request.user, playerName__tournament__current=True):
            pick_list.append(pick.playerName.pk)
        data = json.dumps(pick_list)
        return HttpResponse(data, content_type="application/json")
    else:
        print ('not ajax')
        raise Http404


class PicksListView(LoginRequiredMixin,ListView):
    login_url = 'login'
    redirect_field_name = 'golf_app/pick_list.html'
    model = Picks

    def get_context_data(self,**kwargs):
        context = super(PicksListView, self).get_context_data(**kwargs)
        context.update({
        #'field_list': Field.group,
        'tournament': Tournament.objects.get(current=True),
        'picks_list': Picks.objects.filter(playerName__tournament__current=True,user=self.request.user),
        })
        return context


class ScoreListView(DetailView):
    template_name = 'golf_app/scores.html'
    model=TotalScore

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get('pk') == None:
            tournament = Tournament.objects.get(current=True)
            self.kwargs['pk'] = str(tournament.pk)
        print ('dispatch', self.kwargs)
        return super(ScoreListView, self).dispatch(request, *args, **kwargs)

    def get(self, request, **kwargs):

        no_thru_display = ['cut', 'mdf', 'not started']

        try:
            tournament = Tournament.objects.get(pk=self.kwargs.get('pk'))
            start_time = datetime.datetime.now()
            if datetime.date.today() >= tournament.start_date:
                scores = calc_score.calc_score(self.kwargs, request)
                end_time= datetime.datetime.now()
                summary_data = optimal_picks.optimal_picks(tournament)
                print('sum', summary_data)
                print ('exec time: ', start_time, end_time, end_time-start_time)

                return render(request, 'golf_app/scores.html', {'scores':scores[0],
                                                            'detail_list':scores[1],
                                                            'leader_list':scores[2],
                                                            'cut_data':scores[3],
                                                            'lookup_errors': scores[4],
                                                            'tournament': tournament,
                                                            'thru_list': no_thru_display,
                                                            'optimal_picks': summary_data[0],
                                                            'best_score': summary_data[1],
                                                            'cuts': summary_data[2]
                                                            })
            else:
                tournament = Tournament.objects.get(current=True)
                user_dict = {}
                for user in Picks.objects.filter(playerName__tournament=tournament).values('user__username').annotate(Count('playerName')):
                    user_dict[user.get('user__username')]=user.get('playerName__count')
                scores=calc_score.calc_score(self.kwargs, request)
                print ('lookup_errors', scores[4])
                return render(request, 'golf_app/pre_start.html', {'user_dict': user_dict,
                                                                'tournament': tournament,
                                                                'lookup_errors': scores[4],
                                                                'thru_list': no_thru_display
                                                                })
        except Exception as e:
            print ('score error msg:', e)
            return HttpResponse("Error, please come back closer to the tournament start or Line John to tell him something is broken.")


class SeasonTotalView(ListView):
    template_name="golf_app/season_total.html"
    model=Tournament

    def get_context_data(self, **kwargs):
        display_dict = {}
        user_list = []
        winner_dict = {}
        winner_list = []
        total_scores = {}

        for user in TotalScore.objects.values('user_id').distinct().order_by('user_id'):
            user_key = user.get('user_id')
            user_list.append(User.objects.get(pk=user_key))
            winner_dict[User.objects.get(pk=user_key)]=0
            total_scores[User.objects.get(pk=user_key)]=0

        for tournament in Tournament.objects.filter(season__current=True):
            score_list = []
            for score in TotalScore.objects.filter(tournament=tournament).order_by('user_id'):
                score_list.append(score)
                total_score = total_scores.get(score.user)
                total_scores[score.user] = total_score + score.score
            if tournament.complete:
                winner = TotalScore.objects.filter(tournament=tournament).order_by('score').values('score')
                winning_score = winner[0].get('score')
                #winning_score = winner[0].score
                num_of_winners = winner.filter(score=winning_score, tournament=tournament).count()
                win_user_list = []
                if num_of_winners == 1:
                    winner_data = ([TotalScore.objects.get(tournament=tournament, score=winning_score)], num_of_winners)
                    win_user_list.append(User.objects.get(pk=winner_data[0][0].user.pk))
                    score_list.append(User.objects.get(pk=winner_data[0][0].user.pk))
                    winner_data = (win_user_list, num_of_winners)
                    winner_list.append(winner_data)
                    print ('win1', winner_list)
                elif num_of_winners > 1:
                    winner_data = ([TotalScore.objects.filter(tournament=tournament, score=winning_score)], num_of_winners)
                    #win_user_list = []
                    for user in winner_data[0]:
                        print ('this', user)
                        for name in user:
                            print ('this 2', name)
                        #score_list.append(User.objects.get(pk=name.user.pk))
                            win_user_list.append(User.objects.get(pk=name.user.pk))
                            winner_data = (win_user_list, num_of_winners)
                            score_list.append(User.objects.get(pk=name.user.pk))
                        winner_list.append(winner_data)

                else:
                     print ('something wrong with winner lookup', 'num of winners: ', len(winner))

            display_dict[tournament] = score_list

        #for user in TotalScore.objects.values('user').distinct().order_by('user_id'):
        #    winner_dict[(User.objects.get(pk=user.get('user')))]=0

        print ('this 4', winner_list)
        for winner in winner_list:
            for data in winner[0]:
                print ('this 3', winner[1])
                prize = winner_dict.get(data)
                prize = prize + (30/winner[1])
                winner_dict[data] = prize

        total_score_list = []
        for score in total_scores.values():
            total_score_list.append(score)
        #display_dict['totals']=total_score_list

        ranks = ss.rankdata(total_score_list, method='min')
        rank_list = []
        for rank in ranks:
            rank_list.append(rank)


        print ('display_dict')
        print (display_dict)
        print ('winner dict')
        print (winner_dict)

        context = super(SeasonTotalView, self).get_context_data(**kwargs)
        context.update({
        'display_dict':  display_dict,
        'user_list': user_list,
        'rank_list': rank_list,
        'totals_list': total_score_list,
        'prize_list': winner_dict,

        })
        return context


def setup(request):

    if request.method == "GET":
        if request.user.is_superuser:
           return render(request, 'golf_app/setup.html')
        else:
           return HttpResponse('Not Authorized')
    if request.method == "POST":
        url_number = request.POST.get('tournament_number')
        print (url_number, type(url_number))
        try:
            if Tournament.objects.filter(pga_tournament_num=str(url_number), season__current=True).exists():
                error_msg = ("tournament already exists" + str(url_number))
                return render(request, 'golf_app/setup.html', {'error_msg': error_msg})
            else:
                print ('creating field A')
                populateField.create_groups(url_number)
                return HttpResponseRedirect(reverse('golf_app:field'))
        except ObjectDoesNotExist:
            print ('creating field')
            populateField.create_groups(url_number)
            return HttpResponseRedirect(reverse('golf_app:field'))
        except Exception as e:
            print ('error', e)
            error_msg = (e)
            return render(request, 'golf_app/setup.html', {'error_msg': error_msg})

class AboutView(TemplateView):
    template_name='golf_app/about.html'
