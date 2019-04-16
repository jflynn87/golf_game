#import os
#os.environ.setdefault("DJANGO_SETTINGS_MODULE","gamesProj.settings")

#import django
#django.setup()
import urllib3
from golf_app.models import Field, Group, Tournament
from golf_app import calc_score
from golf_app.calc_score import formatRank

from django.shortcuts import render, get_object_or_404, redirect

def optimal_picks(tournament, ranks):
       '''takes no input, loops thru groups to find low scores'''

       scores = {}
       totalScore = 0
       score_list = {}
       cuts_dict = {}
       min_score = {}

       tournament=Tournament.objects.get(pk=tournament.pk)
       #ranks = calc_score.getRanks({'pk': tournament.pk})[0]
       #field = Field.objects.filter(tournament=tournament)
       #print ('ranks', ranks)

       for group in Group.objects.filter(tournament=tournament):
           group_cuts = 0
           for player in Field.objects.filter(tournament=tournament, group=group):
               if str(player) in ranks.keys():  #needed to deal wiht WD's before start of tourn.
                  #if ranks[player.playerName][0] != "cut":
                    if ranks[player.playerName][0] not in  ["cut", "mdf"] and ranks[player.playerName][0] != '':
                        score_list[str(player)] = int(formatRank(ranks[player.playerName][0]))
                    else:
                        if ranks[player.playerName][0] == "cut":
                            group_cuts += 1
               else:
                    continue


           cuts_dict[group] = group_cuts, group.playerCnt
           scores[group]=score_list
           score_list = {}
           total_score = 0

       if len(scores) != 0:
          for group, golfers in scores.items():
              try:
                  leader = (min(golfers, key=golfers.get))
                  total_score += golfers.get(leader)
                  min_score[group] = leader, golfers.get(leader)
              except Exception as e:
                  print ('optimal scores exception', e)
                  min_score[group] = "None", None


       return min_score, total_score, cuts_dict
