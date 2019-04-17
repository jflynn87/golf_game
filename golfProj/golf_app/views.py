from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, FormView
from golf_app.models import Field, Tournament, Picks, Group, TotalScore, ScoreDetails, mpScores, \
    League, Season, Invite, Player
from golf_app.forms import  PlayerForm, UserCreateForm, LeagueForm, InviteForm, \
    InviteFormSet, CodeForm, UpdateInviteFormSet
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpRequest
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateResponseMixin
from django.urls import reverse, reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
import datetime
from golf_app import populateField, calc_score, optimal_picks
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Min, Q, Count, Sum
import scipy.stats as ss
from django.http import JsonResponse
import json
import random
from django.db import transaction
from django.forms.models import model_to_dict
from django.core.signing import Signer
from golfProj import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives, EmailMessage


class HomePage(TemplateView):
    template_name='index.html'

    def get_context_data(self, **kwargs):
        context = super(HomePage, self).get_context_data(**kwargs)
        #user = User.objects.get(username=self.request.user)
        if self.request.user.is_authenticated and Player.objects.filter(name=self.request.user).exists():
            print ('update context')
            context.update({
            'player': Player.objects.get(name=self.request.user)
            })
        return context

class SignUp(CreateView):
    form_class = UserCreateForm
    #success_url = 'index'
    template_name = 'golf_app/signup.html'

    def get_context_data(self, **kwargs):

        if self.kwargs.get('token') != None:
            invite = Invite.objects.get(code=self.kwargs.get('token'))
            data = {'email': invite.email_address}
            form = UserCreateForm(initial=data)
            player_form = PlayerForm()
        elif self.kwargs.get('pk') != None:
            user = User.objects.get(pk=self.kwargs.get('pk'))
            print (user.password)
            player = Player.objects.get(name=self.request.user)
            player_form = PlayerForm(initial={'avatar': player.avatar})
            form = UserCreateForm(initial={'username': user.username,
                            'password1': user.password,
                            'password2': user.password,
                            'email': player.email,
                            })
        else:
            form = UserCreateForm()
            player_form = PlayerForm()
        context = super(SignUp, self).get_context_data(**kwargs)
        context.update({
        'form': form,
        'player_form': player_form,
        'league': invite.league,
        })

        return context

    def form_invalid(self, form, *args, **kwargs):
        print ('form invalid', form.errors)
        print (self.request.FILES)
        player = PlayerForm(self.request.POST)
        print ('player', player['avatar'])
        return render (self.request, 'golf_app/signup.html', {
                                'form': form,
                                'player_form': player,
        })

    @transaction.atomic
    def form_valid(self, form, *args, **kwargs):
        print (self.request.FILES)
        user_form = UserCreationForm(self.request.POST)
        player_form = PlayerForm(self.request.FILES)
        print ('player form', player_form)
        if user_form.is_valid() and player_form.is_valid():
            user = user_form.save()

            #if the user has an invite, the token will be presnt,
            #if not the invite will be created when creating a league
            #need to add logic for dulpicates and out of order registration

            if self.kwargs.get('token') != None:
                invite = Invite.objects.get(code=self.kwargs.get('token'))
                invite.registered=True
                invite.save()
                #cd = player_form.cleaned_data
                #player = Player()
                player = player_form.save(commit=False)
                player.invite = invite
                player.league = invite.league
                player.name = user
                player.avatar = self.request.FILES
                print (player)
                player.save()

            login(self.request, user)

            return HttpResponseRedirect(reverse_lazy('index'))

        else:
            print ('in form_invalid')
            return render (request, 'golf_app/signup.html', {
                                    'form': user_form,
                                    'player_form': player_form,
            })


class LeagueCreateView(LoginRequiredMixin, CreateView):
    login_url= 'login'
    form_class = LeagueForm
    model = League

    def get_context_data(self, **kwargs):
        context = super(LeagueCreateView, self).get_context_data(**kwargs)
        formset = InviteFormSet()
        context.update({
        'formset': formset,
        })
        return context

    def form_valid(self, form, *args, **kwargs):
        save = save_league_data(self.request, form, *args, **kwargs)

        if save[0] == 'success':

            return redirect('golf_app:view_league', pk=save[1].pk)
        else:
            print ('formset errors', invite_form_set.errors)
            return super(LeagueCreateView, self, save[1]).form_invalid(form)


class LeagueUpdateView(LoginRequiredMixin, UpdateView):
    login_url = 'login'
    form_class = LeagueForm
    model = League

    def get_context_data(self, **kwargs):
        context = super(LeagueUpdateView, self).get_context_data(**kwargs)
        formset = UpdateInviteFormSet(queryset=Invite.objects.filter(league=League.objects.get(pk=self.kwargs.get('pk'))))
        context.update({
        'formset': formset,
        })

        return context

    def form_valid(self, form, *args, **kwargs):
        print (form)
        save = save_league_data(self.request, form, *args, **kwargs)

        if save[0] == 'success':
            return redirect('golf_app:view_league', pk=save[1].pk)
        else:
            print ('formset errors', invite_form_set.errors)
            return super(LeagueUpdateView, self, save[1]).form_invalid(form)


class LeagueDeleteView(LoginRequiredMixin, CreateView):
    pass



@transaction.atomic
def save_league_data(view_object, form, *args, **kwargs):
    '''called from create and update leagues to avoid duplication.  takes a request \
    object, league form and args. returns a tuple with a success/fail string in index [0] \
    and a league object if successful or the invite formset if not in index [1]'''

    user = view_object.user
    invite_form_set = InviteFormSet(view_object.POST)
    print ('form valids', form.is_valid(), invite_form_set.is_valid())
    if form.is_valid() and invite_form_set.is_valid():
        league_cd = form.cleaned_data

        form = form.save(commit=False)
        form.owner = user
        form.season = Season.objects.get(current=True)
        print ('form', form.avatar)
        form.save()

        league = League.objects.get(league=league_cd.get('league'))
        invite_list = []
        for invite_form in invite_form_set:
            if invite_form.has_changed():
                invite_cd = invite_form.cleaned_data
                invite = Invite()
                invite.email_address = invite_cd.get('email_address')
                invite.league = league
                signer = Signer()
                signed_value = signer.sign(invite_cd.get('email_address'))
                invite.code = signed_value.split(':')[1:]
                invite.save()
                invite_list.append(invite)

        player, created = Player.objects.get_or_create(league=league, name=view_object.user)
        player.email = user.email
        player.save()

        print (view_object.get_host())
        if len(invite_list) > 0:
            send_invites(view_object, invite_list)

        return 'success', league
    else:
        return 'fail', invite_form_set


def send_invites(request, invites):
    '''takes a request and a dict of invite id's and email addresses'''

    print ('invites', invites)

    domain = request.get_host()
    protocol = request.scheme

    dir = settings.BASE_DIR + '/golf_app/templates/golf_app/'

    for invite in invites:
        print (invite.code, type(invite.code))
        msg_plain = render_to_string(dir + 'email.txt', {'invite': invite})
        msg_html = render_to_string(dir + 'invite_email.html', {'protocol': protocol,
                                                    'domain': domain,
                                                    'invite': invite})
        print(msg_html)
        send_mail("Welcome to golf pick 'em " + 'Group:  ' +  str(invite.league.league),
        msg_plain,
        "jflynn87g@gmail.com",
        [invite.email_address],
        html_message=msg_html,
        )

    return


def ajax_resend_invites(request):
    '''used by ajax requests, takes a request determines what invites to resend'''

    if request.is_ajax():
        invite_list = []
        data = request.POST
        invite_json_list = json.loads(data['invite_list'])
        i = 0

        while i < len(invite_json_list):
            invite = Invite.objects.get(pk=invite_json_list[i])
            # check if email updated on web page in resend
            if invite.email_address != invite_json_list[i+1]:
                invite.email_address = invite_json_list[i+1]
                invite.save()
            invite_list.append(invite)
            i += 2

        send_invites(request, invite_list)

        return HttpResponse(json.dumps(data), content_type="application/json")
    else:
        print ('bad request ajax_resend_invites')
        raise Http404



class LeagueView(LoginRequiredMixin, DetailView):
    login_url = 'login'
    model = League
    template_name = 'golf_app/view_league.html'

    #def get_queryset(self):
    #    return League.objects.get(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super(LeagueView, self).get_context_data(**kwargs)
        user = self.request.user
        #league = League.objects.get(season__current=True, owner=user)
        invites = Invite.objects.filter(league=League.objects.get(pk=self.kwargs.get('pk')))

        context.update ({
        #        'league': league,
                'invites': invites
        })

        return context


class JoinLeagueView(LoginRequiredMixin, FormView):
    login_url = 'login'
    #redirect_field_name = 'next'
    template_name = 'golf_app/code.html'
    form_class = CodeForm
    #model = Invite

    #def get_redirect_field_name(self):
    #    return 'golf_app/join_league'

    def form_valid(self, form, **kwargs):

        if form.is_valid():
            return redirect('golf_app:signup', token=form.cleaned_data.get('code'))
        else:
            return super(JoinLeagueView, self).form_valid(form)

class UserProfile(LoginRequiredMixin, TemplateView):
    login_url = 'login'
    template_name = 'golf_app/user_profile.html'

    def get_context_data(self, **kwargs):
        context = super(UserProfile, self).get_context_data(**kwargs)
        user = User.objects.get(pk=self.request.user.pk)
        player = Player.objects.get(name=user)
        player_form = PlayerForm(initial={'avatar': player.avatar})

        context.update({
        'user': user,
        'player_form': player_form,
        'player': player
        })
        return context

    def post(self, request, **kwargs):
        print (self.request.FILES)
        #player_form = PlayerForm(self.request.FILES)
        #if player_form.is_valid():
        player = Player.objects.get(name=request.user)
        player.avatar = self.request.FILES.get('avatar')

        player.save()
        player_form = PlayerForm(initial={'avatar': player.avatar})
        message = "Updates Successful"
        return render(request, 'golf_app/user_profile.html', {
                                        'user': self.request.user,
                                        'player_form': player_form,
                                        'player': player,
                                        'message': message,
            })
        #else:
        #    print ('bad form')
        #return super(UserProfile, self).post(request, **kwargs)




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
                error_message = 'The following golfers have withdrawn:' + str(wd_list)
                for wd in wd_list:
                    Field.objects.filter(tournament=tournament, playerName=wd).update(withdrawn=True)

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

    @transaction.atomic
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
                random_picks.append(random.choice(Field.objects.filter(tournament=tournament, group=g, withdrawn=False)))
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
        return super(ScoreListView, self).dispatch(request, *args, **kwargs)

    def get(self, request, **kwargs):

        no_thru_display = ['cut', 'mdf', 'not started']

        #try:
        tournament = Tournament.objects.get(pk=self.kwargs.get('pk'))
        start_time = datetime.datetime.now()
        if datetime.date.today() >= tournament.start_date:
                if tournament.pga_tournament_num != '470': #special logic for match play
                    scores = calc_score.calc_score(self.kwargs, request)
                    calc_finish = datetime.datetime.now()
                    print ('calc time', calc_finish - start_time)
                    summary_data = optimal_picks.optimal_picks(tournament, scores[5])
                    print ('summary time', datetime.datetime.now() - calc_finish)
                    #print('sum', summary_data)
                    #print ('exec time: ', start_time, end_time, end_time-start_time, self.request.user)
                    end_time= datetime.datetime.now()
                    print ('exec time: ', end_time-start_time, self.request.user)

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
                # special logic for match play
                    from golf_app import mp_calc_scores
                    if not tournament.complete:
                        mp_calc_scores.mp_calc_scores(tournament, request)
                    picks = Picks.objects.filter(playerName__tournament=tournament)
                    scores = mpScores.objects.filter(player__tournament=tournament)
                    score_details = ScoreDetails.objects.filter(pick__playerName__tournament=tournament).order_by('user')
                    #score = ScoreDetails.objects.filter(pick__playerName__tournament=tournament).values('user__username').annotate(score=Sum('score')).order_by('score')
                    return render(request, 'golf_app/mp_picks.html', {
                                                            'picks': picks,
                                                            'scores': scores,
                                                            'tournament': tournament,
                                                            'score_details': score_details,
                                                            'total_score': TotalScore.objects.filter(tournament=tournament).order_by('score')
                    })

        else:
                tournament = Tournament.objects.get(current=True)
                user_dict = {}
                for user in Picks.objects.filter(playerName__tournament=tournament).values('user__username').annotate(Count('playerName')):
                    user_dict[user.get('user__username')]=user.get('playerName__count')
                if tournament.pga_tournament_num == '470': #special logic for match player
                    scores = (None, None, None, None,None)
                else:  scores=calc_score.calc_score(self.kwargs, request)
                print ('lookup_errors', scores[4])
                return render(request, 'golf_app/pre_start.html', {'user_dict': user_dict,
                                                                'tournament': tournament,
                                                                'lookup_errors': scores[4],
                                                                'thru_list': no_thru_display
                                                                })
        #except Exception as e:
        #    print ('score error msg:', e)
        #    return HttpResponse("Error, please come back closer to the tournament start or Line John to tell him something is broken.")


class SeasonTotalView(ListView):
    template_name="golf_app/season_total.html"
    model=Tournament

    def get_context_data(self, **kwargs):
        display_dict = {}
        user_list = []
        winner_dict = {}
        winner_list = []
        total_scores = {}
        second_half_scores = {}
        mark_date = datetime.datetime.strptime('2019-3-20', '%Y-%m-%d')

        for user in TotalScore.objects.values('user_id').distinct().order_by('user_id'):
            user_key = user.get('user_id')
            user_list.append(User.objects.get(pk=user_key))
            winner_dict[User.objects.get(pk=user_key)]=0
            total_scores[User.objects.get(pk=user_key)]=0
            #added second half for Mark
            second_half_scores[User.objects.get(pk=user_key)]=0

        for tournament in Tournament.objects.filter(season__current=True).order_by('-start_date'):
            score_list = []
            #second_half_score_list = []  #added for Mark
            for score in TotalScore.objects.filter(tournament=tournament).order_by('user_id'):
                score_list.append(score)
                total_score = total_scores.get(score.user)
                total_scores[score.user] = total_score + score.score
                #add second half for Mark
                if tournament.start_date > mark_date.date():
                    #second_half_score_list.append(score)
                    second_half_score = second_half_scores.get(score.user)
                    second_half_scores[score.user] = second_half_score + score.score

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
                elif num_of_winners > 1:
                    winner_data = ([TotalScore.objects.filter(tournament=tournament, score=winning_score)], num_of_winners)
                    #win_user_list = []
                    for user in winner_data[0]:
                        print ('this', user)
                        for name in user:
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


        for winner in winner_list:
            for data in winner[0]:
                prize = winner_dict.get(data)
                prize = prize + (30/winner[1])
                winner_dict[data] = prize

        total_score_list = []
        total_second_half_score_list = []
        for score in total_scores.values():
            #print ('fh', total_score_list)
            total_score_list.append(score)
        #added for Mark
        for s in second_half_scores.values():
            #print ('sh', second_half_score_list)
            total_second_half_score_list.append(s)

        ranks = ss.rankdata(total_score_list, method='min')
        rank_list = []
        for rank in ranks:
            rank_list.append(rank)

        second_half_ranks = ss.rankdata(total_second_half_score_list, method='min')
        second_half_rank_list = []
        for rank in second_half_ranks:
            second_half_rank_list.append(rank)



        print ()
        print ('display_dict', display_dict)
        print ()
        print ('winner dict', winner_dict)
        print ('second half totals', total_second_half_score_list)
        print ('full season totals',total_score_list)

        context = super(SeasonTotalView, self).get_context_data(**kwargs)
        context.update({
        'display_dict':  display_dict,
        'user_list': user_list,
        'rank_list': rank_list,
        'totals_list': total_score_list,
        'second_half_list': total_second_half_score_list,
        'prize_list': winner_dict,
        'second_half_rank_list': second_half_rank_list,

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
