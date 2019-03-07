import urllib3
from golf_app.models import Field, Tournament, Picks, Group, TotalScore, ScoreDetails, BonusDetails
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count

def calc_score(t_args, request=None):
        '''takes in a request, caclulates and returns the score to the web site.
            Deletes all before starting'''
        print('running calc scores')
        scores = {}
        totalScore = 0
        cut_bonus = True
        winner_bonus = False
        picked_winner = False
        print ('calc scores getting picks')
        picks_dict = getPicks(t_args)
        print ('calc score back from picks')
        ranks_tuple = getRanks(t_args)
        print ('tuple', ranks_tuple)
        ranks = ranks_tuple[0]
        lookup_errors = ranks_tuple[1]
        cutNum = getCutNum(ranks)
        print ('test', cutNum)

        leaders = {}
        for player, rank in ranks.items():
            if player not in ('cut number', 'round', 'cut_status', 'finished'):
                if rank[0] in ('1', 'T1'):
                    leaders[player]=(rank[1])

        cut_data = {}
        if ranks.get('round') != 1:
            cut_info = ranks.get("cut_status")
            cut_data[cut_info[0]]=cut_info[1]

        lookup_errors_dict = {}
        display_detail = {}
        tournament = Tournament.objects.get(pk=t_args.get('pk'))

        for player, picks in picks_dict.items():
            user = User.objects.get(username=player)

            lookup_errors_list = []
            display_list = []
            if tournament.complete == False:
                print ('current tourny score logic')
                print (picks)
                for pick in picks:
                    try:
                        if ranks[pick][0] == 'cut':
                            cut_bonus = False
                            pickRank = cutNum +1
                        elif ranks[pick][0]== '':
                            pickRank = 0
                        elif ranks[pick][0] == "mdf":
                            mdfNum = 0
                            for k, v in ranks.items():
                                if k not in ('cut number', 'round', 'cut_status', 'finished') \
                                and v[0] != 'cut':
                                  if v[1] == 'even':
                                      mdf_score = 0
                                  else:
                                      mdf_score = int(v[1])
                                  if ranks[pick][1] == 'even':
                                      score = 0
                                  else:
                                      score = int(ranks[pick][1])
                                  if mdf_score < score or v[0] not in ['cut', 'mdf']:
                                    mdfNum += 1
                            pickRank = mdfNum + 1
                            print ("MDF", pick, pickRank)
                        else:
                            pickRank_str = (formatRank(ranks[pick][0]))
                            print ('in not cut logic', pick, cutNum, int(pickRank_str))
                            if ranks.get('cut number') != None and cutNum > 0:
                                if int(pickRank_str) > cutNum:
                                    pickRank = cutNum +1
                                else:
                                    pickRank = int(pickRank_str)
                            else:
                                print ('cut num none but > 0, can not get here')
                                pickRank = int(pickRank_str)

                    #shouldn't need the try/except, keeping just in case
                    except (ObjectDoesNotExist, KeyError) as e:
                        print (pick + ' lookup failed', e)
                        lookup_errors_list.append(pick)
                        lookup_errors_dict[user]=lookup_errors_list
                        pickRank = cutNum +1
                        cut_bonus = False

                    if pick in lookup_errors:
                        lookup_errors_list.append(pick)

                    totalScore += pickRank
                    pick_obj = Picks.objects.get(user=user, playerName__playerName=pick, playerName__tournament=tournament)
                    score_detail, created = ScoreDetails.objects.get_or_create(user=user, pick__playerName__tournament=tournament, pick=pick_obj)

                    if ranks.get(pick) != None:
                        score_detail.score = pickRank
                        score_detail.toPar = ranks[pick][1]
                        score_detail.today_score = ranks[pick][2]
                        score_detail.thru = ranks[pick][3]
                        score_detail.sod_position = ranks[pick][4]
                        score_detail.save()
                        display_list.append(score_detail)

                    if pickRank == 1 and ranks.get('finished'):
                        picked_winner = True
                        winner_group = pick_obj.playerName.group.number
                        print ('picked winner', score_detail.user.username, score_detail.pick.playerName, winner_group)

                if lookup_errors_list:
                    lookup_errors_dict[user]=lookup_errors_list

                base_bonus = 50

                if picked_winner:
                    print ('in picked_winner if')
                    winner_bonus = base_bonus + (winner_group * 2)
                    print ('winner bonus', winner_bonus)
                    totalScore -= winner_bonus
                else:
                    winner_bonus = 0

                if ranks.get('cut_status')[0] != "No cut this week":
                    if cut_bonus and ranks.get('round') >2:
                        cut = base_bonus
                        totalScore -= cut
                    else:
                        cut = 0
                else:
                    cut = 0

                bonus_detail, created = BonusDetails.objects.get_or_create(user=user, tournament=tournament)
                bonus_detail.winner_bonus=winner_bonus
                bonus_detail.cut_bonus=cut
                bonus_detail.save()
                display_list.append(bonus_detail)
                ## trying to add a cut count to player overall score display
                cut_count = ScoreDetails.objects.filter(pick__playerName__tournament=tournament, today_score="cut", user=user).aggregate(cuts=Count('user'))
                scores[user] = (cut_count.get('cuts'), totalScore)
                ## end of cut count section

                totalScore = 0
                picked_winner = False
                cut_bonus = True

                display_detail[user]=display_list

                for k, v in sorted(scores.items(), key=lambda x:x[1]):
                    total_score, created = TotalScore.objects.get_or_create(user=User.objects.get(username=k), tournament=tournament)
                    print (total_score)
                    total_score.score = int(v[1])
                    total_score.cut_count = int(v[0])
                    total_score.save()

            else:
                print ('display with no save for old tournament', user)
                for pick in ScoreDetails.objects.filter(user=user, pick__playerName__tournament=tournament):
                    display_list.append(pick)
                display_list.append(BonusDetails.objects.get(user=user, tournament=tournament))
                display_detail[user]=display_list
                display_list = []

        display_scores = TotalScore.objects.filter(tournament=tournament).order_by('score')

        sorted_scores = {}
        if request:
            if not request.user.is_authenticated:
                print ('debug setup A', request)
                sorted_list = []
                for score in TotalScore.objects.filter(tournament=tournament).order_by('score'):
                    for sd in ScoreDetails.objects.filter(user=score.user, pick__playerName__tournament=tournament):
                        sorted_list.append(sd)
                    bd, created = BonusDetails.objects.get_or_create(user=score.user, tournament=tournament)
                    sorted_list.append(bd)
                    user= User.objects.get(pk=score.user.pk)

                    sorted_scores[user]= sorted_list
                    sorted_list = []
            else:
                print ('debug setup', request)
                sorted_list = []
                for s in ScoreDetails.objects.filter(user=request.user, pick__playerName__tournament=tournament):
                    sorted_list.append(s)
                bd, created = BonusDetails.objects.get_or_create(user=request.user, tournament=tournament)
                sorted_list.append(bd)
                user = User.objects.get(pk=request.user.pk)
                sorted_scores[user]=sorted_list
                for score in TotalScore.objects.filter(tournament=tournament).exclude(user=request.user).order_by('score'):
                    sorted_list = []
                    for sd in ScoreDetails.objects.filter(user=score.user, pick__playerName__tournament=tournament):
                        sorted_list.append(sd)
                    bd, created = BonusDetails.objects.get_or_create(user=score.user, tournament=tournament)
                    sorted_list.append(bd)
                    sorted_scores[score.user]= sorted_list

        print ('sortd scores', sorted_scores)
        print ('display det', display_detail)
        if tournament.complete is False and ranks.get('finished') == True:
            tournament.complete = True
            tournament.save()

        #return display_scores, display_detail, leaders, cut_data, lookup_errors_dict
        return display_scores, sorted_scores, leaders, cut_data, lookup_errors_dict


def getPicks(tournament):
            '''retrieves pick objects and returns a dictionary'''
            picks_dict = {}
            pick_list = []

            tournament = Tournament.objects.get(pk=tournament.get('pk'))
            users = User.objects.all()

            for user in User.objects.all():
                if Picks.objects.filter(user=user, playerName__tournament__name=tournament):
                    for pick in Picks.objects.filter(user=user, playerName__tournament__name=tournament).order_by('playerName__group__number'):
                        pick_list.append(str(pick.playerName))
                    picks_dict[str(user)] = pick_list
                    pick_list = []

            return (picks_dict)


def getRanks(tournament):
            '''takes a dict with a touenamnet number. goes to the PGA web site and pulls back json file of tournament ranking/scores'''

            import urllib.request
            import json
            print (tournament.get('pk'))
            json_url = Tournament.objects.get(pk=tournament.get('pk')).score_json_url
            print (json_url)

            with urllib.request.urlopen(json_url) as field_json_url:
                    data = json.loads(field_json_url.read().decode())

            ranks = {}

            if data['leaderboard']['cut_line']['paid_players_making_cut'] == None:
                ranks['cut number']=len(data["leaderboard"]['players'])
                #ranks['cut number']=0
                cut_score = None
                cut_state = "No cut this week"
                print ("cut num = " + str(ranks))
            else:
                cut_section = data['leaderboard']['cut_line']
                cut_players = cut_section["cut_count"]
                ranks['cut number']=cut_players
                cut_score = data['leaderboard']['cut_line']['cut_line_score']
                cut_status = data['leaderboard']['cut_line']['show_projected']
                if cut_status is True:
                    cut_state = "Projected"
                else:
                    cut_state = "Actual"
            ranks['cut_status'] = cut_state, cut_score

            round = data['debug']["current_round_in_setup"]
            ranks['round']=round

            #started = data['leaderboard']['is_started']
            #ranks['started'] = started

            finished = data['leaderboard']['is_finished']
            ranks['finished']=finished

            #tournament = Tournament.objects.get(pk=tournament.get('pk'))
            #if tournament.complete is False and finished:
            #    tournament.complete = True
            #    tournament.save()

            print ('finished = ' + str(finished))


            for row in data["leaderboard"]['players']:
                last_name = row['player_bio']['last_name'].replace(', Jr.', '')
                first_name = row['player_bio']['first_name']
                player = (first_name + ' ' + last_name)
                if (row["current_position"] is '' and round in (2,3,4)) and row['status'] != 'mdf' or row["status"] == "wd":
                    rank = 'cut'
                    if row['status'] == 'wd':
                        score = "WD"
                        sod_position = ''
                    else:
                        score = format_score(row["total"])
                        sod_position = 'cut'
                    today_score = 'cut'
                    thru = ''

                else:
                    if row['status'] == 'mdf':
                        score = format_score(row["total"])
                        rank = 'mdf'
                        sod_position = row["start_position"]
                        today_score = "mdf"
                    else:
                        rank = row["current_position"]
                        score = format_score(row["total"])
                        today_score = format_score(row["today"])
                    if today_score == 'not started':
                        thru = ''
                    else:
                        thru = row['thru']
                    sod_position = row["start_position"]

                ranks[player] = rank, score, today_score, thru, sod_position

            print ('field size from json', len(data["leaderboard"]['players']))
            print ('field size from db ', len(Field.objects.filter(tournament__pk=tournament.get('pk'))))

            lookup_errors = []
            #if len(ranks) - 4 == len(Field.objects.filter(tournament__pk=tournament.get('pk'))):
            #    print ("no WDs")
            #else:
            for golfer in Field.objects.filter(tournament__pk=tournament.get('pk')):
                    if golfer.formatted_name() not in ranks.keys():
                        #ranks[golfer.formatted_name()] = ('cut', 'WD', 'cut', '', 'cut')
                        lookup_errors.append(golfer.formatted_name())

            #print ('calc_score.getRanks()', ranks, lookup_errors)
            return ranks, lookup_errors

def format_score(score):
    '''takes in a sting and returns a string formatted for the right display or calc'''
    if score == None:
        return "not started"
    if score == 0:
        return 'even'
    elif score > 0:
        return ('+' + str(score))
    else:
        return score


def formatRank(rank):
    '''takes in a sting and returns a string formatted for the right display or calc'''
    if rank == '':
       return rank
    elif rank[0] != 'T':
       return rank
    elif rank[0] == 'T':
       return rank[1:]
    else:
       return rank

def getCutNum(ranks):
    """takes in a dict made from the PGA json file and returns an int of the cut
    number to apply to cut picks.  also applies for witdrawls"""
    if ranks.get('cut_status')[0] == "No cut this week":
        print ('adjusting for withdrawls')
        wd = 0
        for key, value in ranks.items():
            if key not in ['cut number', 'cut_status', 'round', 'finished']:
                 if value[0] == 'cut':
                     wd += 1
        cutNum = (len(ranks) - 4) - wd  # -4 non players in dict then -WD
    else:
        if ranks.get('round') == 1:
            cutNum = 70
        else:
            cutNum = ranks.get('cut number')

    print ('cut num function', cutNum)
    return cutNum
