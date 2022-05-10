from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User

COUNT_POSTS = 10


def index(request):
    template = 'posts/index.html'
    post_list = Post.objects.all()
    paginator = Paginator(post_list, COUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    title = 'Последние обновления на сайте'
    context = {
        'title': title,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    """Страница на которой будут посты, отфильтрованные по группам."""
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.post_group.all()
    paginator = Paginator(posts, COUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, template, {
        'group': group,
        'page_obj': page_obj,
    }
    )


def profile(request, username):
    """Страница на которой будут посты, отфильтрованные по автору"""

    author = get_object_or_404(User, username=username)
    user = request.user
    following = (user.is_authenticated
                 and Follow.objects.filter(user=user,
                                           author=author).exists())
    posts = Post.objects.filter(author=author)
    counter_posts = posts.count()
    paginator = Paginator(posts, COUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'user': user,
        'following': following,
        'author': author,
        'counter_posts': counter_posts,
        'page_obj': page_obj,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    one_post = get_object_or_404(Post, pk=post_id)
    posts = Post.objects.filter(author=one_post.author)
    user = request.user
    posts_count = posts.count()
    form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post=one_post)
    context = {
        'user': user,
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
    post = get_object_or_404(Post, pk=post_id)
    is_edit = True
    if post.author != request.user:
        return redirect('posts:post_detail', post.pk)
    if request.method != "POST":
        form = PostForm(instance=post)
        return render(request, 'posts/create_post.html', {
                      'form': form, 'is_edit': is_edit, 'post': post})
    form = PostForm(request.POST or None, files=request.FILES or None,
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
    paginator = Paginator(posts, COUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    title = "Последние посты ваших друзей"
    context = {'title': title,
               'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        if not (Follow.objects.filter(user=request.user,
                                      author=author)).exists():
            Follow.objects.create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)
