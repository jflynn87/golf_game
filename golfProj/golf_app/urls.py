from django.conf.urls import url
from django.urls import path
from golf_app import views

#Template tagging
app_name = 'golf_app'

urlpatterns= [
    url(r'^field/$',views.FieldListView.as_view(),name='field'),
    #url(r'^user_login/$',views.user_login,name="user_login"),
    #url(r'^register/$',views.register,name='register'),
    url(r'^picks_list/$',views.PicksListView.as_view(),name='picks_list'),
    url(r'^scores/$',views.ScoreListView.as_view(),name='scores'),
    url(r'^scores/(?P<pk>\d+)/$',views.ScoreListView.as_view(),name='scores'),
    url(r'^total_score/$',views.SeasonTotalView.as_view(),name='total_score'),
    url(r'^setup/$',views.setup,name='setup'),
    url(r'^about/$',views.AboutView.as_view(),name='about'),
    url(r'^ajax/get_picks/$', views.get_picks, name='get_picks'),
    #url(r'^make_picks/$',views.CreatePicksView.as_view(),name='make_picks'),  # for form



]
