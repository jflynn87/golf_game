from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from golf_app.models import  Field, Picks, Group, Player, League, Season, Invite
from django.db.models import Max
from django.forms.models import modelformset_factory
from django_select2 import *
from django_select2.forms import ModelSelect2Widget




class UserCreateForm(UserCreationForm):
    class Meta:
        fields = ('username', 'email', 'password1', 'password2',)
        model = get_user_model()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label= "Display Name"
        self.fields['email'].label = "Email Address"
        self.fields['email'].help_text = '* Only used if you need to reset your password'
        self.fields['username'].help_text = '* You can use your real name or a nickname'
        self.fields['password1'].help_text = "* Password must be 8 characters"
        self.fields['password2'].help_text = "* Enter the same password as before, for verification."


class PlayerForm(forms.ModelForm):

    class Meta:
        model = Player
        fields = ['avatar',]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].label = "Upload a Picture or Avatar (optional)"
        self.fields['avatar'].required = False

class LeagueForm(forms.ModelForm):

    class Meta:
        model = League
        #fields = ['league', 'message', 'season']
        fields = '__all__'
        widgets = {
        'message': forms.Textarea(attrs= {'rows':3, 'cols':50, 'style': 'width: 100%'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        season = Season.objects.get(current=True)
        self.fields['league'].label = "Group Name"
        self.fields['message'].widget.attrs['placeholder']= "Message to include in invitation email"
        self.fields['season'].queryset = Season.objects.filter(current=True)
        self.fields['season'].initial = season
        self.fields['season'].widget = forms.HiddenInput()
        self.fields['owner'].widget = forms.HiddenInput()


class InviteForm(forms.ModelForm):

    class Meta:
        model = Invite
        fields = ['email_address',]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email_address'].label = ''
        self.fields['email_address'].widget.attrs['placeholder'] = 'name@email.com'



InviteFormSet = modelformset_factory(Invite, InviteForm, extra=2)


#class CreatePicksForm(forms.ModelForm):

#     class Meta:
#         model = Picks
#         fields = ('playerName',)
#         playerName = forms.ModelChoiceField(queryset=Field.objects.filter(tournament__current=True),
#         #playerName = forms.ModelChoiceField(queryset=Field.objects.all(),
#         widget = forms.RadioSelect)
#
#
# group_cnt = Group.objects.filter(tournament__current=True).aggregate(Max('number'))
# print ('group_cnt', group_cnt)
# PickFormSet = modelformset_factory(Picks, form=CreatePicksForm, max_num=group_cnt.get('number_max'))
# NoPickFormSet = modelformset_factory(Picks, form=CreatePicksForm, extra=group_cnt.get('number_max'))



# class CreatePicksForm(forms.ModelForm):
#      #CHOICES = get_choices()
#      playerName = forms.ModelChoiceField(queryset=Field.objects.all(), widget=forms.RadioSelect())
#      model = Field
#
#      def get_choices(self):
#          field = Field.objects.all()
#          choice_list = []
#
#          for group in field:
#              choice_list.append(group.group)
#              for player in group:
#                  palyers = players + player.playerName
#              choice_list.append(players)
#          print (player_list)
#          return player_list
