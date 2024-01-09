from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def get_page_context(request, queryset):
    paginator = Paginator(queryset, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return {
        'paginator': paginator,
        'page_number': page_number,
        'page_obj': page_obj,
    }


def index(request):
    """Главная страница."""
    context = get_page_context(request, Post.objects.all())
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Страница публикаций по группам."""
    group = get_object_or_404(Group, slug=slug)
    context = {
        'group': group,
    }
    context.update(get_page_context(request, group.posts.all()))
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Страница профиля пользователя."""
    author = get_object_or_404(User, username=username)
    post_quantity = author.posts.all().count
    following = request.user.username and Follow.objects.filter(
        user=request.user, author=author).exists()
    context = {
        'author': author,
        'post_quantity': post_quantity,
        'following': following,
    }
    context.update(get_page_context(request, author.posts.all()))
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Страница конкретного поста."""
    form = CommentForm(request.POST or None)
    post = get_object_or_404(Post, id=post_id)
    author = get_object_or_404(User, id=post.author_id)
    comments = post.comments.all()
    post_quantity = author.posts.all().count
    context = {
        'post': post,
        'author': author,
        'post_quantity': post_quantity,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Создать новый пост."""
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    new_post = form.save(commit=False)
    new_post.author = request.user
    form.save()
    return redirect('posts:profile', new_post.author)


@login_required
def post_edit(request, post_id):
    """Редактирование поста."""
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    if not form.is_valid():
        context = {
            'form': form,
            'post': post,
            'is_edit': True,
        }
        return render(request, 'posts/create_post.html', context)
    form.save()
    return redirect('posts:post_detail', post_id)


@login_required
def add_comment(request, post_id):
    """Комментирование поста."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id)


@login_required
def follow_index(request):
    """Посты авторов, на которых подписан текущий пользователь."""
    context = get_page_context(request, Post.objects.filter(
        author__following__user=request.user))
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Подписка на автора."""
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    """Отписка от автора."""
    author = get_object_or_404(User, username=username)
    unfollow = Follow.objects.filter(
        user=request.user, author=author)
    unfollow.delete()
    return redirect('posts:profile', username=username)
