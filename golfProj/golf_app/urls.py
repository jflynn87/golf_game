from django.conf.urls import url
#from django.urls import path
from golf_app import views
from django.contrib.auth import views as auth_views


#Template tagging
app_name = 'golf_app'

urlpatterns= [

    url(r'^signup/$', views.SignUp.as_view(),name='signup'),
    url(r'^login/$', auth_views.LoginView.as_view(template_name='golf_app/login.html'),name='login'),
    #url(r'^logout/$', views.HomePage.as_view(),name='logout'),
    url(r'^logout/$',auth_views.LogoutView.as_view(),name='logout'),
    url(r'^field/$',views.FieldListView.as_view(),name='field'),
    url(r'^create_league/$',views.LeagueCreateView.as_view(),name='create_league'),
    url(r'^view_league/$',views.LeagueView.as_view(),name='view_league'),
    url(r'^update_league/(?P<pk>\d+)/$',views.LeagueUpdateView.as_view(),name='update_league'),
    url(r'^delete_league/(?P<pk>\d+)/$',views.LeagueDeleteView.as_view(),name='delete_league'),
    url(r'^join_league/$',views.JoinLeagueView.as_view(),name='join_league'),
    url(r'^picks_list/$',views.PicksListView.as_view(),name='picks_list'),
    url(r'^scores/$',views.ScoreListView.as_view(),name='scores'),
    url(r'^scores/(?P<pk>\d+)/$',views.ScoreListView.as_view(),name='scores'),
    url(r'^total_score/$',views.SeasonTotalView.as_view(),name='total_score'),
    url(r'^setup/$',views.setup,name='setup'),
    url(r'^about/$',views.AboutView.as_view(),name='about'),
    url(r'^ajax/get_picks/$', views.get_picks, name='get_picks'),
    #url(r'^make_picks/$',views.CreatePicksView.as_view(),name='make_picks'),  # for form



]
