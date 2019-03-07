import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE","golfProj.settings")

import django
django.setup()
from golf_app.models import Picks, Field, Group, Tournament, TotalScore, ScoreDetails, Name, Season
import urllib3
from django.core.exceptions import ObjectDoesNotExist
from golf_app import calc_score


def clean_db():
    print ('in clean db')
    from golf_app.management.commands.clear_models import Command

    Command()


def get_pga_worldrank():
    '''Goes to PGA web site takes no input, goes to web to get world golf rankings and returns a dictionary with player name as a string and key, ranking as a string in values'''

    from bs4 import BeautifulSoup
    import urllib.request

    html = urllib.request.urlopen("https://www.pgatour.com/stats/stat.186.html")
    #html = request.get("https://www.pgatour.com/stats/stat.186.html")
    soup = BeautifulSoup(html, 'html.parser')


    rankslist = (soup.find("div", {'class': 'details section'}))

    ranks = {}

    for row in rankslist.find_all('tr')[1:]:
        try:
            player = (row.find('td', {'class': 'player-name'}).text).strip('\n')
            rank = row.find('td').text.strip('\n').strip(' ')
            ranks[player.capitalize()] = int(rank)
        except Exception as e:
            print(e)

    return ranks



def get_worldrank():
    '''Goes to OWGR web site takes no input, goes to web to get world golf rankings and returns a dictionary with player name as a string and key, ranking as a string in values'''

    from bs4 import BeautifulSoup
    import urllib.request

    html = urllib.request.urlopen("http://www.owgr.com/ranking?pageNo=1&pageSize=All&country=All")
    soup = BeautifulSoup(html, 'html.parser')


    rankslist = (soup.find("div", {'class': 'table_container'}))

    ranks = {}


    for row in rankslist.find_all('tr')[1:]:
        try:
            player = (row.find('td', {'class': 'name'}).text).replace('(Am)','').replace(' Jr','').replace('(am)','')
            rank = row.find('td').text
            ranks[player.capitalize()] = int(rank)
        except Exception as e:
            print(e)

    return ranks


def get_field(tournament_number):
    '''takes a tournament number, goes to web to get field and returns a list with player names'''

    from bs4 import BeautifulSoup
    import json
    import urllib.request
    import datetime

    season = Season.objects.get(current=True)

    # try:
    #     last_tournament = Tournament.objects.get(current=True)
    #     last_tournament.current = False
    #     last_tournament.save()
    # except ObjectDoesNotExist:
    #     print ("no current tournament")

    json_url = 'https://statdata.pgatour.com/r/' + str(tournament_number) +'/field.json'
    print (json_url)

    with urllib.request.urlopen(json_url) as field_json_url:
        data = json.loads(field_json_url.read().decode())

    tourny = Tournament()
    tourny.name = data["Tournament"]["TournamentName"]
    tourny.season = season
    start_date = datetime.date.today()
    print (start_date)
    while start_date.weekday() != 3:
        start_date += datetime.timedelta(1)
    tourny.start_date = start_date
    #tourny.start_date = data["Tournament"]["yyyy"] + '-' +data["Tournament"]["mm"] + '-' + data["Tournament"]["dd"]
    tourny.field_json_url = json_url
    tourny.score_json_url = 'https://statdata.pgatour.com/r/' + str(tournament_number) +'/' + str(season) + '/leaderboard-v2mini.json'
    tourny.pga_tournament_num = tournament_number
    tourny.current=True
    tourny.complete=False
    tourny.save()

    #Tournament.objects.get_or_create(season=season, name=tourny.name,start_date=tourny.start_date, field_json_url=tourny.field_json_url, score_json_url=tourny.score_json_url, current=True, complete=False)


    field_list = {}


    for player in data["Tournament"]["Players"][0:]:
        #name = (' '.join(reversed(player["PlayerName"].split(', ')))).replace('Jr.','')
        name = (' '.join(reversed(player["PlayerName"].split(', '))).replace(' Jr.','').replace('(am)',''))
        try:
            if player["isAlternate"] == "Yes":
                #exclude alternates from the field
                alternate = True
            else:
                alternate = False
                field_list[name] = alternate
        except IndexError:
            alternate = False
            print (player + 'alternate lookup failed')




    return field_list


def configure_groups(field_list):
    '''takes a list, calculates the number of groups and players per group'''

    group_cnt = 1
    groups = {}
    if len(field_list) > 119:
        group_size = 10

        while group_cnt <6:
            groups[group_cnt] = group_size
            group_cnt += 1

        group_size = 15
        remainder = (len(field_list)-50) % group_size

        remaining_groups = (len(field_list)-(remainder+50))/group_size

        while group_cnt < remaining_groups + 5:
             groups[group_cnt] = group_size
             group_cnt += 1
    elif len(field_list) < 20:
        print ('less than 20')
        group_size = 3
        total_groups = int(len(field_list)/group_size)
        remainder = len(field_list) % (total_groups*group_size)
        while group_cnt < total_groups:
            groups[group_cnt] = group_size
            group_cnt +=1
    else:
        group_size = int(len(field_list)/10)
        remainder = len(field_list) % (group_size*10)
        total_groups = (len(field_list)-(remainder))/group_size

        while group_cnt < total_groups:
            groups[group_cnt] = group_size
            group_cnt +=1

    #for last group, same logig regardless of field size
    if remainder == 0:
        groups[group_cnt] = group_size
    else:
        groups[group_cnt] = group_size + remainder



    for k,v in groups.items():
        Group.objects.get_or_create(tournament=Tournament.objects.get(current=True), number=k,playerCnt=v)[0]

    print (groups)
    return groups


def create_groups(tournament_number):

    '''takes in a date as a pick deadline and a tournament number for pgatour.com to get json files for the field and score'''

    season = Season.objects.get(current=True)

    if Tournament.objects.filter(season=season).count() > 0:
        try:
            last_tournament = Tournament.objects.get(current=True, complete=True, season=season)
            last_tournament.current = False
            last_tournament.save()
            key = {}
            key['pk']=last_tournament.pk
            calc_score.calc_score(key)

        except ObjectDoesNotExist:
            print ('no current tournament')
    else:
        print ('setting up first tournament of season')

    field = get_field(tournament_number)
    OWGR_rankings =  get_worldrank()
    PGA_rankings = get_pga_worldrank()
    configure_groups(field)

    tournament = Tournament.objects.get(current=True, season=season)

    print (len(field))

    group_dict = {}
    name_switch = False

    for player in field:

        print ('player before', player)
        if Name.objects.filter(PGA_name=player).exists():
            name_switch = True
            name = Name.objects.get(PGA_name=player)
            player = name.OWGR_name
            print ('owgr after', player)
            print ('pga player', name)


        rank = OWGR_rankings.get(player.capitalize())

        if rank == None:
            rank = PGA_rankings.get(player.capitalize())

            if rank == None:
                print (player)
                rank = 9999

        if name_switch:
            player = name.PGA_name
            name_switch = False

        group_dict[player] = [rank, field.get(player)]

    player_cnt = 1
    group_num = 1

    groups = Group.objects.get(tournament=tournament, number=group_num)

    print ('group_dict before field save', group_dict)
    for k, v in sorted(group_dict.items(), key=lambda x: x[1]):
        if player_cnt < groups.playerCnt:
          print (k,v[0], str(groups.number), str(groups.playerCnt))
          Field.objects.get_or_create(tournament=tournament, playerName=k, currentWGR=v[0], group=groups, alternate=v[1])[0]
          player_cnt +=1
        elif player_cnt == groups.playerCnt:
          print (k,v[0], str(groups.number), str(groups.playerCnt))
          Field.objects.get_or_create(tournament=tournament, playerName=k, currentWGR=v[0], group=groups, alternate=v[1])[0]
          group_num +=1
          player_cnt = 1
          if Field.objects.filter(tournament=tournament).count() < len(field):
             groups = Group.objects.get(tournament=tournament,number=group_num)


if __name__ == '__main__':
    print ('populating script!')
    #clean_db()
    #create_groups()

    print ("Populating Complete!")
