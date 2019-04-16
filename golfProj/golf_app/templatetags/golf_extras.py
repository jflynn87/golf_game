from django import template
from golf_app.models import Picks, mpScores, Field, Tournament, Group
from django.db.models import Count


register = template.Library()

@register.filter
def model_name(obj):
    return obj._meta.verbose_name

@register.filter
def currency(dollars):
    dollars = int(dollars)
    return '$' + str(dollars)

@register.filter
def line_break(count):
    user_cnt = Picks.objects.filter(playerName__tournament__current=True).values('playerName__tournament').annotate(Count('user', distinct=True))
    if (count -1) % (user_cnt[0].get('user__count')) == 0 or count == 0:
        return True
    else:
        return False

@register.filter
def first_round(pick):
    field = Field.objects.get(tournament__pga_tournament_num='470', playerName=pick)
    wins = mpScores.objects.filter(player=field, round__lt=4, result="Yes").count()
    losses = mpScores.objects.filter(player=field, round__lt=4, result="No").exclude(score="AS").count()
    ties = mpScores.objects.filter(player=field, round__lt=4, score="AS").count()

    return str(wins) + '-' + str(losses) + '-' + str(ties)

@register.filter
def leader(group):
    #print ('group', group)
    tournament = Tournament.objects.get(pga_tournament_num="470")
    grp = Group.objects.get(tournament=tournament,number=group)
    field = Field.objects.filter(tournament=tournament, group=grp)
    golfer_dict = {}

    for golfer in field:
        golfer_dict[golfer.playerName] = int(first_round(golfer.playerName)[0]) + (.5*int(first_round(golfer.playerName)[4]))

    #print ('leader', [k for k, v in golfer_dict.items() if v == max(golfer_dict.values())])
    winner= [k for k, v in golfer_dict.items() if v == max(golfer_dict.values())]
    return winner
