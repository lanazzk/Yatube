from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from posts.utils import get_paginator

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User


def index(request):
    posts = Post.objects.all()
    page_obj = get_paginator(posts, request)
    title = 'Последние обновления на сайте'
    context = {
        'title': title,
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Страница на которой будут посты, отфильтрованные по группам."""
    group = get_object_or_404(Group, slug=slug)
    posts = group.post_group.all()
    page_obj = get_paginator(posts, request)

    return render(request, 'posts/group_list.html', {
        'group': group,
        'page_obj': page_obj,
    }
    )


def profile(request, username):
    """Страница на которой будут посты, отфильтрованные по автору"""

    author = get_object_or_404(User, username=username)
    following = (request.user.is_authenticated
                 and Follow.objects.filter(user=request.user,
                                           author=author).exists())
    posts = Post.objects.filter(author=author)
    counter_posts = posts.count()
    page_obj = get_paginator(posts, request)
    context = {
        'following': following,
        'author': author,
        'counter_posts': counter_posts,
        'page_obj': page_obj,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    one_post = get_object_or_404(Post, pk=post_id)
    author = get_object_or_404(User, username=one_post.author)
    posts_count = author.post_author.count()
    form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post=one_post)
    context = {
        'posts_count': posts_count,
        'one_post': one_post,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    form.save()
    return redirect('posts:profile', post.author)


@login_required
def post_edit(request, post_id):
    is_edit = True
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post.pk)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {
                      'form': form, 'is_edit': is_edit, 'post': post})
    form.save()
    return redirect('posts:post_detail', post.pk)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = get_paginator(posts, request)
    title = "Последние посты ваших друзей"
    context = {'title': title,
               'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)
