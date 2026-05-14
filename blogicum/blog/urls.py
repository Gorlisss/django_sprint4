from django.urls import include, path, reverse_lazy
from . import views
from django.contrib.auth.forms import UserCreationForm
from django.views.generic.edit import CreateView

app_name = "blog"  # namespace

urlpatterns = [
    path("", views.IndexListView.as_view(), name="index"),
    path("posts/<int:id>/", views.post_detail, name="post_detail"),
    path(
        "category/<slug:category_slug>/",
        views.CategoryPostsListView.as_view(),
        name="category_posts"
    ),
    path('auth/', include('django.contrib.auth.urls')),
    path(
        'auth/registration/',
        CreateView.as_view(
            template_name='registration/registration_form.html',
            form_class=UserCreationForm,
            success_url=reverse_lazy('blog:index'),
        ),
        name='registration',
    ),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/",
         views.ProfileListView.as_view(),
         name="profile"),
    path('posts/<int:post_id>/edit/', views.PostUpdateView.as_view(),
         name='edit_post'),
    path('posts/<int:post_id>/delete/', views.PostDeleteView.as_view(), name='delete_post'),
    path('posts/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('posts/<int:post_id>/edit_comment/<int:comment_id>/', views.edit_comment, name='edit_comment'),
    path('posts/<int:post_id>/delete_comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('posts/create/', views.PostCreateView.as_view(), name='create_post'),
]
