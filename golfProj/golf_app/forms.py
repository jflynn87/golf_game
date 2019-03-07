from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from golf_app.models import  Field, Picks, Group
from django.db.models import Max
from django.forms.models import modelformset_factory
from django_select2 import *
from django_select2.forms import ModelSelect2Widget
from django.forms.formsets import BaseFormSet




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
