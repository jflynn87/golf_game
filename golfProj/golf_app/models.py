from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


# Create your models here.

class Season(models.Model):
    season = models.CharField(max_length=10, null=True)
    current = models.BooleanField()

    def __str__(self):
        return self.season

class League(models.Model):
    STAKES_CHOICES = (
        ('1', "Weekly"),
        ('2', "Season 50/50"),
        ('3', "Season 75/25")
    )
    league = models.CharField(max_length=100, unique=True)
    stakes_types = models.CharField(max_length=1,choices=STAKES_CHOICES, null=True)
    stakes = models.IntegerField(default=0)
    no_cut_bonus = models.IntegerField(default=-50)
    winner_bonus = models.IntegerField(default=-50)
    message = models.CharField(max_length=1000, null=True, blank=True)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)


    def __str__(self):
        return self.league

class Invite(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='invite')
    email_address = models.EmailField()
    registered = models.BooleanField(default=False)
    code = models.CharField(max_length=100, null=True)

    def __str__(self):
        return str (self.email_address)

class Player(models.Model):
    #invite = models.ForeignKey(Invite, on_delete=models.CASCADE, related_name='player')
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='player')
    name = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='static/golf_app/avatar/', null=True, blank=True)

    def __str__(self):
        return str(self.name)


class Tournament(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    name = models.CharField(max_length=264)
    start_date = models.DateField(null=True)
    field_json_url = models.URLField(null=True)
    score_json_url = models.URLField(null=True)
    current = models.BooleanField(default=False)
    complete = models.BooleanField(default=False)
    pga_tournament_num = models.CharField(max_length=10, null=True)

    #def get_queryset(self):
    #    return self.objects.filter().first()

    def __str__(self):
        return self.name


class Group(models.Model):
    tournament= models.ForeignKey(Tournament, on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    playerCnt = models.PositiveIntegerField()

    def __str__(self):
        return str(self.number) + '-' + str(self.tournament)


class Field(models.Model):
    playerName = models.CharField(max_length = 256, null=True)
    currentWGR = models.IntegerField(unique=False, null=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    alternate = models.NullBooleanField(null=True)

    class Meta:
        ordering = ['group', 'currentWGR']

    def __str__(self):
        return  self.playerName

    def get_absolute_url(self):
        return reverse("golf_app:show_picks",kwargs={'pk':self.pk})

    def get_group(self, args):
        group = self.objects.filter(group=args)
        return group

    #def current_field(self):
    #    return self.objects.filter(tournament__current=True)

    def formatted_name(self):
        return self.playerName.replace(' Jr.','').replace('(am)','')

    def withdrawal(self):
        pass




class Name(models.Model):
    OWGR_name = models.CharField(max_length=256)
    PGA_name = models.CharField(max_length=256)

    def __str__(self):
        return self.OWGR_name


class Picks(models.Model):
    #playerName = models.ForeignKey(Field, on_delete=models.CASCADE, blank=True, default='', null=True)
    playerName = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='picks')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(null=True)

    class Meta():
        unique_together = ('playerName', 'user')

    def __str__(self):
        return str(self.playerName) if self.playerName else ''

    def is_winner(self):
        winner = ScoreDetails.objects.get(pick=self, score=1)

        if (self.playerName == winner.pick.playerName and self.playerName.tournament.complete):
           return True
        else:
           return False


class ScoreDetails(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    pick = models.ForeignKey(Picks, on_delete=models.CASCADE, blank=True, null=True)
    score = models.PositiveIntegerField(null=True)
    toPar = models.CharField(max_length=10, null=True)
    today_score = models.CharField(max_length = 10, null=True)
    thru = models.CharField(max_length=100, null=True)
    sod_position = models.CharField(max_length=30, null=True)

    def __str__(self):
        return str(self.user) + str(self.pick) + str(self.score)


class BonusDetails(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True)
    winner_bonus = models.IntegerField(null=True)
    cut_bonus = models.IntegerField(null=True)

    def __str__(self):
        return str(self.user)


class TotalScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True)
    score = models.IntegerField(null=True)
    cut_count = models.IntegerField(null=True)


    class Meta():
        unique_together = ('tournament', 'user')

    def __str__(self):
        return str(self.user) + str(self.score)
