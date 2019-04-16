import urllib3
from golf_app.models import Field, Tournament, Picks, Group, TotalScore, ScoreDetails, BonusDetails, mpScores
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum, Q
import datetime
from django.db import transaction
import urllib
import json
from golf_app.templatetags import golf_extras

@transaction.atomic
def mp_calc_scores(tournament, request=None):
    '''takes a tournament object and option request and returns a dict.  used to calculate
    scores for match play format tournaments'''
    json_url = tournament.score_json_url
    print (json_url)

    with urllib.request.urlopen(json_url) as field_json_url:
        data = json.loads(field_json_url.read().decode())

    field = data['rounds']
    #print (field[3].get('roundNum'))

    round = 1
    cur_round = data.get('curRnd')

    round_status = data.get('curRndState')
    if round_status == 'Official':
        max_round = int(cur_round)
    else:
        max_round = int(cur_round) - 1

    print (round, max_round)

    #print (field[4].get('brackets')[2])
    #print ((field[6]))
    #print ((field[7]))

    #if int(cur_round) < 4:
    while round <= max_round:
        print ('round', round)
        #if round
        if mpScores.objects.filter(round=round).exists():
            print ('scores exist', round)
        else:
            i = 0
            print ('calculating scores', round)
            if round < 4:
                max_i = 4
            elif round == 4:
                max_i = 4
            elif round == 5:
                max_i = 4
            elif round == 6:
                max_i = 1
            elif round == 7:
                max_i = 2
            while i < max_i:
                if round < 4:
                    bracket = field[round-1].get('brackets')[i]
                else:
                    bracket = field[round].get('brackets')[i]
                print ("Bracket: ", bracket.get('bracketNum'), bracket.get('name'))
                j = 0
                if round < 4:
                    max_j = 8
                elif round == 4:
                    max_j = 2
                elif round == 5:
                    max_j = 1
                elif round == 6:
                    max_j = 2
                elif round == 7:
                    max_j =1
                else:  #need to update as i understand bracket format for last 8 and semis/final
                    max_j = 1
                print ('max j', max_j)
                while j < max_j:
                    match_num = bracket.get('groups')[j].get('matchNum')
                    match_score = bracket.get('groups')[j].get('players')[0].get('finalMatchScr')

                    player_name =  bracket.get('groups')[j].get('players')[0].get('fName') + ' ' + bracket.get('groups')[j].get('players')[0].get('lName')
                    player_winner_flag = bracket.get('groups')[j].get('players')[0].get('matchWinner')

                    player2_name =  bracket.get('groups')[j].get('players')[1].get('fName') + ' ' + bracket.get('groups')[j].get('players')[1].get('lName')
                    player2_winner_flag = bracket.get('groups')[j].get('players')[1].get('matchWinner')
                    print (tournament)
                    player_names = []
                    player_names.append(player_name)
                    player_names.append(str(player_name) + ' ')
                    player_names.append(player2_name)
                    player_names.append(str(player2_name) + ' ')
                    #print (player_name, player2_name, len(Picks.objects.filter(playerName__tournament=tournament, playerName__playerName__in=player_names)))

                    for golfer in Field.objects.filter(tournament=tournament, playerName__in=player_names):

                        if golfer.playerName in [player_name, str(player_name + ' ')]:
                            score = mpScores()
                            score.bracket = bracket.get('bracketNum')
                            score.round = round
                            score.match_num = match_num
                            score.player = golfer
                            score.result = player_winner_flag
                            score.score = match_score
                            score.save()
                            print ('saving', golfer.playerName)
                        elif golfer.playerName in [player2_name, str(player2_name + ' ')]:
                            score2 = mpScores()
                            score2.bracket = bracket.get('bracketNum')
                            score2.round = round
                            score2.match_num = match_num
                            score2.player = golfer
                            score2.result = player2_winner_flag
                            score2.score = match_score
                            score2.save()
                            print ('saving', golfer.playerName)
                        else:
                            print ('in mp_calc else', golfer.playerName)

                    j +=1
                i += 1
        round += 1


# for round 1 results
    winners = {}
    winners_list = []
    for group in Group.objects.filter(tournament=tournament):
        player = golf_extras.leader(group.number)
        winners[group]=player
        winners_list.append(player[0])

    if ScoreDetails.objects.filter(pick__playerName__tournament=tournament).exists():
        ScoreDetails.objects.filter(pick__playerName__tournament=tournament).delete()
    for pick in Picks.objects.filter(playerName__tournament=tournament).order_by('user'):
        if pick.playerName.playerName in winners_list:
            #print ('winner', pick.user, pick.playerName.playerName)
            sd = ScoreDetails()
            sd.user = pick.user
            sd.pick = pick
            sd.score = 0
            sd.save()
        #elif str(pick.playerName.playerName) + ' ' in winners_list:
        #    print ('winner 1', pick.user, pick.playerName.playerName)
        else:
            sd = ScoreDetails()
            sd.user = pick.user
            sd.pick = pick
            sd.score = 17
            sd.save()
            #print ('not winner', pick.user, pick.playerName.playerName)

# for final 16 results
    r4_loser_list = mpScores.objects.filter(round=4, result="No").values('player__playerName')
    print (r4_loser_list)

    r5_loser_list = mpScores.objects.filter(round=5, result="No").values('player__playerName')
    print (r5_loser_list)

    finalist = mpScores.objects.filter(round=6.0, result="Yes")
    for player in finalist:
        if mpScores.objects.filter(player=player.player, round=7.0, result="Yes"):
            winner = player
        else:
            second_place = player

    consolation = mpScores.objects.filter(round=6.0, result="No")
    for player in consolation:
        if mpScores.objects.filter(player=player.player, round=7.0, result="Yes"):
            third_place = player
        else:
            forth_place = player


    #forth_place = mpScores.objects.filter(round=6.0, result="No").filter(round=7.0, result = "No")
    #third_place = mpScores.objects.filter(round=6.0, result="No").filter(round=7.0, result = "Yes")
    #second_place = mpScores.objects.filter(round=6.0, result="Yes").filter(round=7.0, result = "No")
    #winner = mpScores.objects.filter(round=6.0, result="Yes").filter(round=7.0, result = "Yes")

    print ('winner', winner)
    print ('2', second_place)
    print ('3', third_place)
    print ('4', forth_place)


    for pick in Picks.objects.filter(playerName__tournament=tournament):
        if r4_loser_list.filter(player__playerName=pick.playerName).exists():
            sd = ScoreDetails.objects.get(pick=pick)
            #sd.user = pick.user
            #sd.pick = pick
            sd.score = 9
            sd.save()

        if r5_loser_list.filter(player__playerName=pick.playerName).exists():
            sd = ScoreDetails.objects.get(pick=pick)
            #sd.user = pick.user
            #sd.pick = pick
            sd.score = 5
            sd.save()

        if forth_place.player.playerName == str(pick.playerName):
            sd = ScoreDetails.objects.get(pick=pick)
            #sd.user = pick.user
            #sd.pick = pick
            sd.score = 4
            sd.save()

        if third_place.player.playerName == str(pick.playerName):
            sd = ScoreDetails.objects.get(pick=pick)
            #sd.user = pick.user
            #sd.pick = pick
            sd.score = 3
            sd.save()

        if second_place.player.playerName == str(pick.playerName):
            sd = ScoreDetails.objects.get(pick=pick)
            #sd.user = pick.user
            #sd.pick = pick
            sd.score = 2
            sd.save()

        if winner.player.playerName == str(pick.playerName):
            sd = ScoreDetails.objects.get(pick=pick)
            #sd.user = pick.user
            #sd.pick = pick
            sd.score = 1
            sd.save()
            bd = BonusDetails.objects.get(user=sd.user, tournament=tournament)
            bd.winner_bonus = 50
            bd.save()


    score = ScoreDetails.objects.filter(pick__playerName__tournament=tournament).values('user_id').annotate(score=Sum('score'))
    #remaining = ScoreDetails.objects.filter(pick__playerName__tournament=tournament, score=0).values('user').annotate(playing=Count('pick'))

    for sd in score:
        user = User.objects.get(pk=sd.get('user_id'))
        bd, created = BonusDetails.objects.get_or_create(user=user, tournament=tournament)
        if created:
            bd.winner_bonus = 0
            bd.cut_bonus = 0
            bd.save()
        ts, created = TotalScore.objects.get_or_create(user=user, tournament=tournament)
        ts.score = sd.get('score') - bd.winner_bonus

        ts.save()


    return
