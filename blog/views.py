from django.shortcuts import render, get_object_or_404
from blog.models import Post


def index(request):
    posts = Post.objects.filter(is_published=True)
    return render(request, "blog/index.html", {"posts": posts})


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    return render(request, "blog/post.html", {"post": post})