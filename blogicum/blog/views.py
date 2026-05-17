"""view.py."""

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Post, Category, Comment
from .forms import ProfileEditForm, PostForm, CommentForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Count
from django.http import Http404


def _base_published_filter(queryset):
    """Базовая фильтрация опубликованных постов."""
    return queryset.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True
    )


def _get_published_posts_with_comments(queryset=None):
    """Возвращает опубликованные посты с аннотацией количества комментариев."""
    if queryset is None:
        queryset = Post.objects.all()
    return _base_published_filter(queryset).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


def _get_posts_with_comments(queryset):
    """Универсальная аннотация комментариев для любого queryset."""
    return queryset.annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление поста."""

    model = Post
    success_url = reverse_lazy('blog:index')
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def test_func(self):
        """Проверка прав."""
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        """Переадрессация при отсутствии прав."""
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование поста."""

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def test_func(self):
        """Проверка прав."""
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        """Переадрессация при отсутствии прав."""
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])

    def get_success_url(self):
        """Переадрессация после редактирвоания."""
        return reverse_lazy('blog:post_detail',
                            kwargs={'post_id': self.kwargs['post_id']})


class IndexListView(ListView):
    """Главная страница со списком всех постов."""

    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        return _get_published_posts_with_comments()


class CategoryPostsListView(ListView):
    """Список постов в определённой категории."""

    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        """Возвращает посты из категории."""
        self.category = get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True
        )
        return _get_published_posts_with_comments(
            self.category.post_set.all()
        )

    def get_context_data(self, **kwargs):
        """Добавляет категорию в контекст шаблона."""
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class ProfileListView(ListView):
    """Страница профиля пользователя со списком его постов."""

    model = Post
    template_name = 'blog/profile.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        """Возвращает посты пользователя."""
        self.profile_user = get_object_or_404(User,
                                              username=self.kwargs['username'])
        if self.request.user == self.profile_user:
            return _get_posts_with_comments(
                Post.objects.filter(author=self.profile_user)
            )
        return _get_published_posts_with_comments(
            Post.objects.filter(author=self.profile_user)
        )

    def get_context_data(self, **kwargs):
        """Добавляет профиль пользователя в контекст шаблона."""
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile_user
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """Создание нового поста."""

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        """Устанавливает автора поста перед сохранением."""
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        """Переадрессация на страницу профиля после создания поста."""
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user.username})


def post_detail(request, post_id):
    """Детальная страница отдельного поста."""
    published_post = _base_published_filter(Post.objects.all()).filter(
        id=post_id).first()

    if published_post:
        post = published_post
    else:
        # Если опубликованного нет, проверяем, может быть это черновик автора
        post = get_object_or_404(Post, id=post_id)

        if not request.user.is_authenticated or request.user != post.author:
            raise Http404("Пост не доступен")

    comments = post.comments.all()
    form = CommentForm()
    context = {'post': post, 'comments': comments, 'form': form}
    return render(request, 'blog/detail.html', context)


@login_required
def edit_profile(request):
    """Редактирование профиля пользователя."""
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'blog/edit_profile.html', {'form': form})


@login_required
def add_comment(request, post_id):
    """Добавление комментария к посту."""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    """Редактирование комментария."""
    comment = get_object_or_404(Comment, pk=comment_id, post__pk=post_id)
    if comment.author != request.user:

        return redirect('blog:post_detail', post_id=post_id)

    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)

    return render(request, 'blog/comment.html',
                  {'form': form, 'comment': comment})


@login_required
def delete_comment(request, post_id, comment_id):
    """Удаление комментария с подтверждением."""
    comment = get_object_or_404(Comment, pk=comment_id, post__pk=post_id)

    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'GET':
        return render(request, 'blog/comment_delete.html',
                      {'comment': comment})
    comment.delete()
    return redirect('blog:post_detail', post_id=post_id)
