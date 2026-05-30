from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json, os, mimetypes

from .recommendation_service import get_recommendations

from .models import (
    User, Category, Author, Book, Rating, Review, Quote,
    Like, Download, ReadLog, CommunityPost, PostComment, SiteStats
)


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)

def json_ok(data=None, **kwargs):
    payload = {'ok': True}
    if data: payload.update(data)
    payload.update(kwargs)
    return JsonResponse(payload)

def json_err(msg, status=400):
    return JsonResponse({'ok': False, 'error': msg}, status=status)



def unique_slug(model, base):
    slug = slugify(base)[:80]
    qs = model.objects.filter(slug__startswith=slug)
    if not qs.exists():
        return slug
    return f"{slug}-{qs.count()}"


# ─── AUTH ──────────────────────────────────────────────────────────────────────
def auth_page(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard' if is_admin(request.user) else 'home')
    return render(request, 'archives/auth.html')


def login_view(request):
    if request.method != 'POST':
        return redirect('auth')
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()
    user = authenticate(request, username=username, password=password)
    if not user:
        return JsonResponse({'ok': False, 'error': 'Invalid username or password.'})
    if user.is_currently_banned:
        until = user.ban_until.strftime('%Y-%m-%d') if user.ban_until else 'indefinitely'
        return JsonResponse({'ok': False, 'error': f'Your account is banned until {until}.'})
    login(request, user)
    user.last_online = timezone.now()
    user.save(update_fields=['last_online'])
    dest = 'admin_dashboard' if is_admin(user) else 'home'
    return JsonResponse({'ok': True, 'redirect': reverse(dest)})


def register_view(request):
    if request.method != 'POST':
        return redirect('auth')
    username  = request.POST.get('username', '').strip()
    full_name = request.POST.get('full_name', '').strip()
    email     = request.POST.get('email', '').strip()
    password  = request.POST.get('password', '').strip()
    if not all([username, full_name, email, password]):
        return JsonResponse({'ok': False, 'error': 'All fields are required.'})
    if len(password) < 6:
        return JsonResponse({'ok': False, 'error': 'Password must be at least 6 characters.'})
    if User.objects.filter(username=username).exists():
        return JsonResponse({'ok': False, 'error': 'Username already taken.'})
    if User.objects.filter(email=email).exists():
        return JsonResponse({'ok': False, 'error': 'Email already registered.'})
    parts = full_name.split(' ', 1)
    user = User.objects.create_user(
        username=username, email=email, password=password,
        first_name=parts[0], last_name=parts[1] if len(parts)>1 else ''
    )
    login(request, user)
    return JsonResponse({'ok': True, 'redirect': '/home/'})


def logout_view(request):
    logout(request)
    return redirect('auth')


@require_GET
def site_stats_api(request):
    stats = _site_stats()
    return JsonResponse({
        'books': stats['total_books'],
        'authors': stats['total_authors'],
        'readers': stats['total_users'],
        'downloads': stats['total_downloads']
    })


# ─── USER PAGES ───────────────────────────────────────────────────────────────
@login_required
def home(request):
    # Trending: most downloaded TODAY (last 24 hours)
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    trending_books = Book.objects.filter(
        is_approved=True,
        downloads__downloaded_at__gte=today_start
    ).annotate(
        today_downloads=Count('downloads', filter=Q(downloads__downloaded_at__gte=today_start))
    ).order_by('-today_downloads')[:6]

    # Only show books that have been downloaded at least once
    popular  = Book.objects.filter(is_approved=True, download_count__gt=0).order_by('-download_count')[:6]
    latest   = Book.objects.filter(is_approved=True).order_by('-created_at')[:6]
    categories = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('-cnt')
    top_authors = Author.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('-cnt')[:8]
    all_authors = Author.objects.order_by('name')
    liked_ids = list(Like.objects.filter(user=request.user).values_list('book_id', flat=True))
    
    # Get stats: visitors/month, daily searches, books, authors
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    visitors_month = User.objects.filter(
        is_superuser=False,
        last_online__gte=thirty_days_ago
    ).count()
    
    today = timezone.now().date()
    try:
        today_stats = SiteStats.objects.get(date=today)
        daily_searches = today_stats.daily_searches
    except SiteStats.DoesNotExist:
        daily_searches = 0
    
    stats = {
        'visitors': visitors_month,
        'daily_searches': daily_searches,
        'total_books': Book.objects.filter(is_approved=True).count(),
        'total_authors': Author.objects.count(),
    }
    
    return render(request, 'archives/home.html', {
        'trending': trending_books, 'popular': popular, 'latest': latest,
        'categories': categories, 'top_authors': top_authors, 'all_authors': all_authors,
        'liked_ids': liked_ids, 'stats': stats,
    })

def _site_stats():
    total_books   = Book.objects.filter(is_approved=True).count()
    total_authors = Author.objects.count()
    total_dl      = Book.objects.filter(is_approved=True).aggregate(s=Sum('download_count'))['s'] or 0
    total_reads   = Book.objects.filter(is_approved=True).aggregate(s=Sum('read_count'))['s'] or 0
    online_users  = User.objects.filter(last_online__gte=timezone.now()-timezone.timedelta(seconds=300)).count()
    total_users   = User.objects.filter(is_superuser=False).count()
    try:
        today = SiteStats.objects.get(date=timezone.now().date())
        visitors = today.visitors
        searches = today.daily_searches
    except SiteStats.DoesNotExist:
        visitors = 0
        searches = 0
    return {
        'total_books': total_books, 'total_authors': total_authors,
        'total_downloads': total_dl, 'total_reads': total_reads,
        'online_users': online_users, 'total_users': total_users,
        'visitors': visitors, 'daily_searches': searches,
    }


@login_required
def categories_page(request):
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('name')
    return render(request, 'archives/categories.html', {'categories': cats})


@login_required
def authors_page(request):
    authors = Author.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('name')
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/authors.html', {'authors': authors, 'categories': cats})


@login_required
def category_books(request, slug):
    cat = get_object_or_404(Category, slug=slug)
    books = Book.objects.filter(is_approved=True, category=cat).order_by('-created_at')
    liked_ids = list(Like.objects.filter(user=request.user).values_list('book_id', flat=True))
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/book_list.html', {
        'books': books, 'title': cat.name, 'subtitle': f'{books.count()} books',
        'liked_ids': liked_ids, 'categories': cats,
    })


@login_required
def search_view(request):
    q = request.GET.get('q', '').strip()
    books = Book.objects.filter(is_approved=True)
    authors_found = Author.objects.none()
    users_found = User.objects.none()
    following_ids = []
    if q:
        books = books.filter(
            Q(title__icontains=q) | Q(description__icontains=q) |
            Q(authors__name__icontains=q) | Q(category__name__icontains=q) |
            Q(publisher__icontains=q)
        ).distinct()
        authors_found = Author.objects.filter(
            Q(name__icontains=q) | Q(nationality__icontains=q) | Q(bio__icontains=q)
        ).annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('-cnt')
        users_found = User.objects.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        ).exclude(is_superuser=True).exclude(id=request.user.id)
        following_ids = list(request.user.following.values_list('following_id', flat=True))
        # increment daily search counter
        today, _ = SiteStats.objects.get_or_create(date=timezone.now().date())
        SiteStats.objects.filter(pk=today.pk).update(daily_searches=today.daily_searches+1)
    liked_ids = list(Like.objects.filter(user=request.user).values_list('book_id', flat=True))
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/book_list.html', {
        'books': books, 'title': f'Search: "{q}"', 'subtitle': f'{books.count()} results',
        'liked_ids': liked_ids, 'categories': cats, 'q': q,
        'authors_found': authors_found, 'users_found': users_found,
        'following_ids': following_ids,
    })


# ─── BOOK DETAIL ──────────────────────────────────────────────────────────────
@login_required
def book_detail(request, slug):
    book = get_object_or_404(Book, slug=slug, is_approved=True)
    # count read
    _, created = ReadLog.objects.get_or_create(book=book, user=request.user)
    if created:
        Book.objects.filter(pk=book.pk).update(read_count=book.read_count+1)
        User.objects.filter(pk=request.user.pk).update(total_reads=request.user.total_reads+1)

    user_rating = Rating.objects.filter(book=book, user=request.user).first()
    user_liked  = Like.objects.filter(book=book, user=request.user).exists()
    liked_ids   = list(Like.objects.filter(user=request.user).values_list('book_id', flat=True))
    reviews     = book.reviews.filter(status='visible').select_related('user')
    quotes      = book.quotes.select_related('user')

    ratings = book.ratings.all()
    average_rating = round(ratings.aggregate(avg=Avg('score'))['avg'] or 0.0, 1)
    rating_count = ratings.count()
    dist = {i: ratings.filter(score=i).count() for i in range(1, 6)}

    # Get recommendations using ML content-based filtering only
    rec_ids = get_recommendations(book.pk, user=request.user, max_results=4, min_similarity=0.5)
    if rec_ids:
        recs_dict = {b.pk: b for b in Book.objects.filter(pk__in=rec_ids, is_approved=True)}
        recs = [recs_dict[id] for id in rec_ids if id in recs_dict]
    else:
        recs = []

    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    top_authors = Author.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('-cnt')[:8]

    return render(request, 'archives/book_detail.html', {
        'book': book, 'user_rating': user_rating, 'user_liked': user_liked,
        'liked_ids': liked_ids, 'reviews': reviews, 'quotes': quotes, 'dist': dist,
        'average_rating': average_rating, 'rating_count': rating_count,
        'recs': recs, 'categories': cats, 'top_authors': top_authors,
        'is_admin': is_admin(request.user),
    })


# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────
@login_required
def download_book(request, slug):
    book = get_object_or_404(Book, slug=slug, is_approved=True)
    if not book.pdf_file:
        return JsonResponse({'ok': False, 'error': 'No file available for this book.'}, status=404)
    _, created = Download.objects.get_or_create(book=book, user=request.user)
    if created:
        Book.objects.filter(pk=book.pk).update(download_count=book.download_count+1)
        User.objects.filter(pk=request.user.pk).update(total_downloads=request.user.total_downloads+1)
    # serve the file
    file_path = book.pdf_file.path
    if not os.path.exists(file_path):
        return JsonResponse({'ok': False, 'error': 'File not found on server.'}, status=404)
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'
    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ─── RATING (AJAX) ────────────────────────────────────────────────────────────
@login_required
@require_POST
def rate_book(request, slug):
    book  = get_object_or_404(Book, slug=slug, is_approved=True)
    score = int(request.POST.get('score', 0))
    if not 1 <= score <= 5:
        return json_err('Score must be between 1 and 5.')
    obj, created = Rating.objects.update_or_create(
        book=book, user=request.user,
        defaults={'score': score}
    )
    avg = book.ratings.aggregate(a=Avg('score'))['a'] or 0
    return json_ok(average=round(avg, 1), count=book.ratings.count(), your_score=score)


# ─── REVIEW (AJAX) ────────────────────────────────────────────────────────────
@login_required
@require_POST
def add_review(request, slug):
    book = get_object_or_404(Book, slug=slug, is_approved=True)
    body = request.POST.get('body', '').strip()
    if not body:
        return json_err('Review cannot be empty.')
    r = Review.objects.create(book=book, user=request.user, body=body)
    return json_ok(
        review_id=r.pk,
        user=request.user.get_full_name() or request.user.username,
        avatar=request.user.avatar.url if request.user.avatar else None,
        body=r.body,
        date=r.created_at.strftime('%b %d, %Y'),
    )


# ─── QUOTE (AJAX) ─────────────────────────────────────────────────────────────
@login_required
@require_POST
def add_quote(request, slug):
    book = get_object_or_404(Book, slug=slug, is_approved=True)
    body = request.POST.get('body', '').strip()
    if not body:
        return json_err('Quote cannot be empty.')
    q = Quote.objects.create(book=book, user=request.user, body=body)
    return json_ok(
        quote_id=q.pk,
        user=request.user.get_full_name() or request.user.username,
        body=q.body,
        date=q.created_at.strftime('%b %d, %Y'),
    )


# ─── LIKE (AJAX) ──────────────────────────────────────────────────────────────
@login_required
@require_POST
def toggle_like(request, slug):
    book = get_object_or_404(Book, slug=slug, is_approved=True)
    obj, created = Like.objects.get_or_create(book=book, user=request.user)
    if not created:
        obj.delete()
        Book.objects.filter(pk=book.pk).update(like_count=max(0, book.like_count-1))
        liked = False
    else:
        Book.objects.filter(pk=book.pk).update(like_count=book.like_count+1)
        liked = True
    return json_ok(liked=liked, like_count=book.likes.count())


# ─── UPLOAD BOOK (user) ───────────────────────────────────────────────────────
@login_required
@require_POST
def upload_book(request):
    title      = request.POST.get('title','').strip()
    desc       = request.POST.get('description','').strip()
    cat_id     = request.POST.get('category_id')
    author_ids = request.POST.getlist('author_ids')
    author_new = request.POST.get('author_new','').strip()
    author_nationality = request.POST.get('author_nationality','').strip()
    author_bio = request.POST.get('author_bio','').strip()
    author_birth_year = request.POST.get('author_birth_year','')
    author_death_year = request.POST.get('author_death_year','')
    author_photo = request.FILES.get('author_photo')
    publisher  = request.POST.get('publisher','').strip()
    isbn       = request.POST.get('isbn','').strip()
    language   = request.POST.get('language','en')
    release    = request.POST.get('release_date','').strip()
    pages      = request.POST.get('pages','')
    pdf        = request.FILES.get('pdf_file')
    cover      = request.FILES.get('cover')

    if not title:
        return json_err('Title is required.')
    if not pdf:
        return json_err('PDF file is required.')

    slug = unique_slug(Book, title)
    cat  = Category.objects.filter(pk=cat_id).first() if cat_id else None
    book = Book(
        title=title, slug=slug, description=desc, category=cat,
        publisher=publisher, isbn=isbn, language=language,
        release_date=release, pages=int(pages) if pages.isdigit() else None,
        is_approved=False,  # User uploads need admin approval
        uploaded_by=request.user,
        extension=(pdf.name.split('.')[-1].upper() if pdf else 'PDF'),
    )
    if pdf:   book.pdf_file = pdf
    if cover: book.cover    = cover
    book.save()

    for aid in author_ids:
        try: book.authors.add(Author.objects.get(pk=int(aid)))
        except: pass

    if author_new:
        author = Author(
            name=author_new,
            nationality=author_nationality,
            bio=author_bio,
            created_by=request.user
        )
        if author_birth_year.isdigit():
            author.birth_year = int(author_birth_year)
        if author_death_year.isdigit():
            author.death_year = int(author_death_year)
        if author_photo:
            author.photo = author_photo
        author.save()
        book.authors.add(author)

    book.file_size = book.file_size_display()
    book.save(update_fields=['file_size'])

    User.objects.filter(pk=request.user.pk).update(total_uploads=request.user.total_uploads+1)
    return json_ok(message='Book uploaded! Pending admin approval.')


# ─── MY LIBRARY ───────────────────────────────────────────────────────────────
@login_required
def my_library(request):
    liked_books     = Book.objects.filter(likes__user=request.user, is_approved=True)
    downloaded_books = Book.objects.filter(downloads__user=request.user, is_approved=True)
    uploaded_books  = Book.objects.filter(uploaded_by=request.user)
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/my_library.html', {
        'liked_books': liked_books,
        'downloaded_books': downloaded_books,
        'uploaded_books': uploaded_books,
        'categories': cats,
    })


# ─── PROFILE ──────────────────────────────────────────────────────────────────
@login_required
def profile(request):
    if request.method == 'POST':
        first = request.POST.get('first_name', '').strip()
        last  = request.POST.get('last_name', '').strip()
        bio   = request.POST.get('bio', '').strip()
        email = request.POST.get('email', '').strip()
        avatar = request.FILES.get('avatar')
        u = request.user
        u.first_name = first or u.first_name
        u.last_name  = last  or u.last_name
        u.bio   = bio
        u.email = email or u.email
        if avatar:
            u.avatar = avatar
        u.save()
        return json_ok(message='Profile updated.')
    liked_count    = Like.objects.filter(user=request.user).count()
    followers_count = request.user.followers.count()
    following_count = request.user.following.count()
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/profile.html', {
        'liked_count': liked_count,
        'followers_count': followers_count,
        'following_count': following_count,
        'categories': cats,
    })


@login_required
def user_profile(request, username):
    """View another user's public profile"""
    user = get_object_or_404(User, username=username, is_superuser=False)
    
    uploaded_books = Book.objects.filter(uploaded_by=user, is_approved=True)
    liked_books = Book.objects.filter(likes__user=user, is_approved=True)
    reviews = Review.objects.filter(user=user, status='visible').select_related('book')
    
    is_following = request.user.following.filter(following=user).exists() if request.user.is_authenticated else False
    followers_count = user.followers.count()
    following_count = user.following.count()
    
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    
    return render(request, 'archives/user_profile.html', {
        'profile_user': user,
        'uploaded_books': uploaded_books,
        'liked_books': liked_books,
        'reviews': reviews,
        'is_following': is_following,
        'followers_count': followers_count,
        'following_count': following_count,
        'categories': cats,
    })


@login_required
@require_POST
def follow_user(request, username):
    """Follow a user"""
    user = get_object_or_404(User, username=username, is_superuser=False)
    
    if user == request.user:
        return json_err('You cannot follow yourself.')
    
    from .models import Follow
    follow_obj, created = Follow.objects.get_or_create(follower=request.user, following=user)
    
    if created:
        return json_ok(message=f'You are now following {user.get_full_name() or user.username}.', following=True)
    else:
        follow_obj.delete()
        return json_ok(message=f'You unfollowed {user.get_full_name() or user.username}.', following=False)


@require_GET
def followers_api(request, username):
    """Get followers of a user"""
    user = get_object_or_404(User, username=username, is_superuser=False)
    from .models import Follow
    
    followers = Follow.objects.filter(following=user).select_related('follower').values_list('follower', flat=True)
    follower_users = User.objects.filter(id__in=followers)
    
    data = {
        'ok': True,
        'followers': [
            {
                'username': u.username,
                'full_name': u.get_full_name() or u.username,
                'avatar': u.avatar.url if u.avatar else None,
                'first_letter': (u.get_full_name() or u.username)[0].upper(),
                'liked_count': u.liked_books.count(),
                'uploaded_count': u.uploaded_books.count(),
                'downloads_count': u.downloads.count(),
                'reads_count': u.read_logs.count()
            }
            for u in follower_users
        ]
    }
    return JsonResponse(data)


@require_GET
def following_api(request, username):
    """Get users that a user is following"""
    user = get_object_or_404(User, username=username, is_superuser=False)
    from .models import Follow
    
    following = Follow.objects.filter(follower=user).select_related('following').values_list('following', flat=True)
    following_users = User.objects.filter(id__in=following)
    
    data = {
        'ok': True,
        'following': [
            {
                'username': u.username,
                'full_name': u.get_full_name() or u.username,
                'avatar': u.avatar.url if u.avatar else None,
                'first_letter': (u.get_full_name() or u.username)[0].upper(),
                'liked_count': u.liked_books.count(),
                'uploaded_count': u.uploaded_books.count(),
                'downloads_count': u.downloads.count(),
                'reads_count': u.read_logs.count()
            }
            for u in following_users
        ]
    }
    return JsonResponse(data)



@login_required
@require_POST
def change_password(request):
    old = request.POST.get('old_password')
    new = request.POST.get('new_password')
    if not request.user.check_password(old):
        return json_err('Current password is incorrect.')
    if len(new) < 6:
        return json_err('New password must be at least 6 characters.')
    request.user.set_password(new)
    request.user.save()
    update_session_auth_hash(request, request.user)
    return json_ok(message='Password changed.')





# ─── COMMUNITY ────────────────────────────────────────────────────────────────
@login_required
def community(request):
    show_mine = request.GET.get('mine') == '1'
    posts_qs = CommunityPost.objects.select_related('author').prefetch_related(
        'post_comments__author'
    ).annotate(
        comment_count=Count('post_comments')
    ).order_by('-created_at')
    if show_mine:
        posts_qs = posts_qs.filter(author=request.user)
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/community.html', {
        'posts': posts_qs,
        'categories': cats,
        'show_mine': show_mine,
        'is_admin': is_admin(request.user),
    })


@login_required
@require_POST
def create_post(request):
    topic = request.POST.get('topic', '').strip()
    body  = request.POST.get('body', '').strip()
    if not topic or not body:
        return json_err('Topic and body are required.')
    p = CommunityPost.objects.create(author=request.user, topic=topic, body=body)
    return json_ok(post_id=p.pk, topic=p.topic,
                   user=request.user.get_full_name() or request.user.username,
                   date=p.created_at.strftime('%b %d, %Y'))


@login_required
@require_POST
def like_post(request, pk):
    post = get_object_or_404(CommunityPost, pk=pk)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    return json_ok(liked=liked, count=post.likes.count())


@login_required
@require_POST
def add_post_comment(request, post_pk):
    post = get_object_or_404(CommunityPost, pk=post_pk)
    body = request.POST.get('body', '').strip()
    if not body:
        return json_err('Comment cannot be empty.')
    comment = PostComment.objects.create(post=post, author=request.user, body=body)
    return json_ok(
        comment_id=comment.pk,
        author=request.user.get_full_name() or request.user.username,
        body=comment.body,
        date=comment.created_at.strftime('%b %d, %Y'),
        can_delete=True,
        comment_count=post.post_comments.count()
    )


@login_required
@require_POST
def like_post_comment(request, pk):
    comment = get_object_or_404(PostComment, pk=pk)
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True
    return json_ok(liked=liked, count=comment.likes.count())


@login_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(CommunityPost, pk=pk)
    if post.author != request.user and not is_admin(request.user):
        return json_err('You are not allowed to delete this post.', status=403)
    post.delete()
    return json_ok()


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(PostComment, pk=pk)
    if comment.author != request.user and not is_admin(request.user):
        return json_err('You are not allowed to delete this comment.', status=403)
    post_pk = comment.post.pk
    comment.delete()
    comment_count = PostComment.objects.filter(post_id=post_pk).count()
    return json_ok(post_pk=post_pk, comment_count=comment_count)


@login_required
@require_POST
def like_quote(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.user in quote.likes.all():
        quote.likes.remove(request.user)
        liked = False
    else:
        quote.likes.add(request.user)
        liked = True
    return json_ok(liked=liked, count=quote.likes.count())


@login_required
@require_POST
def like_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if request.user in review.likes.all():
        review.likes.remove(request.user)
        liked = False
    else:
        review.likes.add(request.user)
        liked = True
    return json_ok(liked=liked, count=review.likes.count())


@login_required
@require_POST
def delete_quote(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if quote.user != request.user and not is_admin(request.user):
        return json_err('You are not allowed to delete this quote.', status=403)
    quote.delete()
    return json_ok()


@login_required
@require_POST
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if review.user != request.user and not is_admin(request.user):
        return json_err('You are not allowed to delete this review.', status=403)
    review.delete()
    return json_ok()


# ─── QUOTES/REVIEWS PAGES ─────────────────────────────────────────────────────
@login_required
def quotes_page(request):
    quotes = Quote.objects.select_related('book', 'user').order_by('-created_at')
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/quotes.html', {'quotes': quotes, 'categories': cats})


@login_required
def reviews_page(request):
    reviews = Review.objects.filter(status='visible').select_related('book','user').order_by('-created_at')
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/reviews_page.html', {'reviews': reviews, 'categories': cats})


# ─── SETTINGS ─────────────────────────────────────────────────────────────────
@login_required
def settings_page(request):
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    return render(request, 'archives/settings.html', {'categories': cats})


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(is_admin, login_url='/')
def admin_dashboard(request):
    stats = _site_stats()
    recent_activity = Download.objects.select_related('user','book').order_by('-downloaded_at')[:10]
    pending_books   = Book.objects.filter(is_approved=False).count()
    flagged_reviews = Review.objects.filter(status='flagged').count()
    all_users       = User.objects.filter(is_superuser=False).order_by('username')
    stats_cards = [
        ('Total Registered Users', stats['total_users'],    '👥', 'gold'),
        ('Users Online Now',        stats['online_users'],  '🟢', 'green'),
        ('Total Downloads',         stats['total_downloads'],'📥', 'blue'),
        ('Books Read / Viewed',     stats['total_reads'],   '📖', 'gold'),
    ]
    return render(request, 'archives/admin/dashboard.html', {
        'stats': stats, 'stats_cards': stats_cards,
        'recent_activity': recent_activity,
        'pending_books': pending_books, 'flagged_reviews': flagged_reviews,
        'all_users': all_users,
    })


@login_required
@user_passes_test(is_admin)
def admin_books(request):
    books = Book.objects.select_related('category','uploaded_by').prefetch_related('authors').order_by('-created_at')
    q = request.GET.get('q','')
    if q:
        books = books.filter(Q(title__icontains=q)|Q(authors__name__icontains=q)).distinct()
    return render(request, 'archives/admin/books.html', {'books': books, 'q': q})


@login_required
@user_passes_test(is_admin)
def admin_community(request):
    posts = CommunityPost.objects.select_related('author').prefetch_related('post_comments').order_by('-created_at')
    q = request.GET.get('q','')
    if q:
        posts = posts.filter(Q(topic__icontains=q)|Q(body__icontains=q)|Q(author__username__icontains=q))
    return render(request, 'archives/admin/community.html', {'posts': posts, 'q': q})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_add_book(request):
    title      = request.POST.get('title','').strip()
    desc       = request.POST.get('description','').strip()
    cat_id     = request.POST.get('category_id')
    author_ids = request.POST.getlist('author_ids')
    author_new = request.POST.get('author_new','').strip()
    publisher  = request.POST.get('publisher','').strip()
    isbn       = request.POST.get('isbn','').strip()
    language   = request.POST.get('language','en')
    release    = request.POST.get('release_date','').strip()
    pages      = request.POST.get('pages','')
    pdf        = request.FILES.get('pdf_file')
    cover      = request.FILES.get('cover')
    is_approved= request.POST.get('is_approved') == '1'
    is_trending= request.POST.get('is_trending') == '1'

    if not title:
        return json_err('Title is required.')

    slug = unique_slug(Book, title)
    cat  = Category.objects.filter(pk=cat_id).first() if cat_id else None
    book = Book(
        title=title, slug=slug, description=desc, category=cat,
        publisher=publisher, isbn=isbn, language=language,
        release_date=release, pages=int(pages) if pages.isdigit() else None,
        is_approved=is_approved, is_trending=is_trending,
        uploaded_by=request.user,
        extension=(pdf.name.split('.')[-1].upper() if pdf else 'PDF'),
    )
    if pdf:   book.pdf_file = pdf
    if cover: book.cover    = cover
    book.save()

    for aid in author_ids:
        try: book.authors.add(Author.objects.get(pk=int(aid)))
        except: pass

    if author_new:
        a, _ = Author.objects.get_or_create(name=author_new, defaults={'created_by': request.user})
        book.authors.add(a)

    book.file_size = book.file_size_display()
    book.save(update_fields=['file_size'])
    return json_ok(book_id=book.pk, message=f'"{title}" added successfully.')


@login_required
@user_passes_test(is_admin)
def admin_edit_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'GET':
        return JsonResponse({
            'title': book.title,
            'description': book.description,
            'category_id': book.category.pk if book.category else None,
            'language': book.language,
            'publisher': book.publisher,
            'isbn': book.isbn,
            'release_date': book.release_date,
            'pages': book.pages,
            'is_approved': book.is_approved,
            'is_trending': book.is_trending,
            'authors': [{'id': a.pk, 'name': a.name} for a in book.authors.all()],
        })
    # POST handling...
    book = get_object_or_404(Book, pk=pk)
    title      = request.POST.get('title','').strip()
    desc       = request.POST.get('description','').strip()
    cat_id     = request.POST.get('category_id')
    author_ids = request.POST.getlist('author_ids')
    author_new = request.POST.get('author_new','').strip()
    publisher  = request.POST.get('publisher','').strip()
    isbn       = request.POST.get('isbn','').strip()
    language   = request.POST.get('language','en')
    release    = request.POST.get('release_date','').strip()
    pages      = request.POST.get('pages','')
    pdf        = request.FILES.get('pdf_file')
    cover      = request.FILES.get('cover')
    is_approved= request.POST.get('is_approved') == '1'
    is_trending= request.POST.get('is_trending') == '1'

    if not title:
        return json_err('Title is required.')

    if book.title != title:
        slug = unique_slug(Book, title)
        book.slug = slug
    cat  = Category.objects.filter(pk=cat_id).first() if cat_id else None

    book.title = title
    book.description = desc
    book.category = cat
    book.publisher = publisher
    book.isbn = isbn
    book.language = language
    book.release_date = release
    book.pages = int(pages) if pages.isdigit() else None
    book.is_approved = is_approved
    book.is_trending = is_trending

    if pdf:
        book.pdf_file = pdf
        book.extension = pdf.name.split('.')[-1].upper()
    if cover:
        book.cover = cover

    book.save()

    # Update authors
    book.authors.clear()
    for aid in author_ids:
        try: book.authors.add(Author.objects.get(pk=int(aid)))
        except: pass

    if author_new:
        a, _ = Author.objects.get_or_create(name=author_new, defaults={'created_by': request.user})
        book.authors.add(a)

    book.file_size = book.file_size_display()
    book.save(update_fields=['file_size'])
    return json_ok(message=f'"{title}" updated successfully.')


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_approve_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    book.is_approved = True
    book.save(update_fields=['is_approved'])
    return json_ok()


@login_required
@user_passes_test(is_admin)
@require_GET
def admin_book_preview(request, pk):
    book = get_object_or_404(Book, pk=pk)
    data = {
        'id': book.pk,
        'title': book.title,
        'description': book.description,
        'category': book.category.name if book.category else None,
        'authors': [a.name for a in book.authors.all()],
        'publisher': book.publisher,
        'isbn': book.isbn,
        'language': book.language,
        'release_date': book.release_date,
        'pages': book.pages,
        'cover_url': book.cover.url if book.cover else None,
        'pdf_url': book.pdf_file.url if book.pdf_file else None,
        'file_size': book.file_size,
        'extension': book.extension,
        'uploaded_by': book.uploaded_by.get_full_name() or book.uploaded_by.username if book.uploaded_by else None,
        'uploaded_at': book.created_at.strftime('%b %d, %Y'),
        'is_approved': book.is_approved,
    }
    return JsonResponse({'ok': True, 'book': data})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    title = book.title
    book.delete()
    return json_ok(message=f'"{title}" deleted.')


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_delete_post(request, pk):
    post = get_object_or_404(CommunityPost, pk=pk)
    topic = post.topic
    post.delete()
    return json_ok(message=f'Post "{topic}" deleted.')


@login_required
@user_passes_test(is_admin)
@require_GET
def admin_post_comments(request, pk):
    post = get_object_or_404(CommunityPost, pk=pk)
    comments = [
        {
            'id': c.pk,
            'author': c.author.username,
            'body': c.body,
            'created_at': c.created_at.strftime('%b %d, %Y %H:%M'),
        }
        for c in post.post_comments.select_related('author').all()
    ]
    return json_ok(comments=comments)


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_delete_post_comment(request, pk):
    comment = get_object_or_404(PostComment, pk=pk)
    comment.delete()
    return json_ok(message='Comment deleted.')


@login_required
@user_passes_test(is_admin)
def admin_categories(request):
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('name')
    return render(request, 'archives/admin/categories.html', {'categories': cats})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_add_category(request):
    name = request.POST.get('name','').strip()
    icon = request.POST.get('icon','📚').strip()
    if not name:
        return json_err('Name is required.')
    if Category.objects.filter(name__iexact=name).exists():
        return json_err('Category already exists.')
    slug = unique_slug(Category, name)
    cat  = Category.objects.create(name=name, icon=icon, slug=slug)
    return json_ok(cat_id=cat.pk, name=cat.name, icon=cat.icon)


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_delete_category(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    cat.delete()
    return json_ok()


@login_required
@user_passes_test(is_admin)
def admin_authors(request):
    authors = Author.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('name')
    return render(request, 'archives/admin/authors.html', {'authors': authors})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_add_author(request):
    name        = request.POST.get('name','').strip()
    nationality = request.POST.get('nationality','').strip()
    bio         = request.POST.get('bio','').strip()
    birth       = request.POST.get('birth_year','')
    death       = request.POST.get('death_year','')
    photo       = request.FILES.get('photo')
    if not name:
        return json_err('Name is required.')
    author = Author(name=name, nationality=nationality, bio=bio, created_by=request.user)
    if birth.isdigit(): author.birth_year = int(birth)
    if death.isdigit(): author.death_year = int(death)
    if photo: author.photo = photo
    author.save()
    return json_ok(author_id=author.pk, name=author.name,
                   photo=author.photo.url if author.photo else None)


@login_required
@user_passes_test(is_admin)
def admin_edit_author(request, pk):
    author = get_object_or_404(Author, pk=pk)
    if request.method == 'GET':
        return JsonResponse({
            'name': author.name,
            'nationality': author.nationality,
            'bio': author.bio,
            'birth_year': author.birth_year,
            'death_year': author.death_year,
            'photo': author.photo.url if author.photo else None,
        })
    # POST
    name        = request.POST.get('name','').strip()
    nationality = request.POST.get('nationality','').strip()
    bio         = request.POST.get('bio','').strip()
    birth       = request.POST.get('birth_year','')
    death       = request.POST.get('death_year','')
    photo       = request.FILES.get('photo')
    if not name:
        return json_err('Name is required.')
    author.name = name
    author.nationality = nationality
    author.bio = bio
    if birth.isdigit(): author.birth_year = int(birth)
    if death.isdigit(): author.death_year = int(death)
    else: author.death_year = None
    if photo: author.photo = photo
    author.save()
    return json_ok(message=f'"{name}" updated successfully.')


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_delete_author(request, pk):
    author = get_object_or_404(Author, pk=pk)
    author.delete()
    return json_ok()


@login_required
@user_passes_test(is_admin)
def admin_users(request):
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return render(request, 'archives/admin/users.html', {'users': users})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_ban_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    duration = int(request.POST.get('days', 30))
    user.status   = 'banned'
    user.ban_until = timezone.now() + timezone.timedelta(days=duration)
    user.save(update_fields=['status','ban_until'])
    return json_ok()


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_unban_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.status    = 'active'
    user.ban_until = None
    user.save(update_fields=['status','ban_until'])
    return json_ok()


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.delete()
    return json_ok()


@login_required
@user_passes_test(is_admin)
def admin_reviews(request):
    reviews = Review.objects.select_related('user','book').order_by('-created_at')
    return render(request, 'archives/admin/reviews.html', {'reviews': reviews})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_remove_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.status = 'removed'
    review.moderated_by = request.user
    review.moderated_at = timezone.now()
    review.save(update_fields=['status','moderated_by','moderated_at'])
    return json_ok()


@login_required
@user_passes_test(is_admin)
@require_GET
def admin_book_comments(request, pk):
    """Get all reviews and quotes for a book"""
    book = get_object_or_404(Book, pk=pk)
    reviews = book.reviews.filter(status='visible').select_related('user').order_by('-created_at')
    quotes = book.quotes.select_related('user').order_by('-created_at')
    
    reviews_data = [
        {
            'id': r.pk,
            'user': r.user.get_full_name() or r.user.username,
            'date': r.created_at.strftime('%b %d, %Y'),
            'body': r.body,
        }
        for r in reviews
    ]
    
    quotes_data = [
        {
            'id': q.pk,
            'user': q.user.get_full_name() or q.user.username,
            'date': q.created_at.strftime('%b %Y'),
            'body': q.body,
        }
        for q in quotes
    ]
    
    return JsonResponse({
        'ok': True,
        'reviews': reviews_data,
        'quotes': quotes_data,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHOR DETAIL VIEW
# ═══════════════════════════════════════════════════════════════════════════════

def author_detail(request, pk):
    author = get_object_or_404(Author, pk=pk)
    books  = Book.objects.filter(authors=author, is_approved=True).order_by('-download_count')
    liked_ids = []
    if request.user.is_authenticated:
        liked_ids = list(Like.objects.filter(user=request.user).values_list('book_id', flat=True))
    cats  = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))
    other = Author.objects.exclude(pk=pk).annotate(cnt=Count('books', filter=Q(books__is_approved=True))).order_by('-cnt')[:10]

    total_downloads = books.aggregate(s=Sum('download_count'))['s'] or 0
    total_reads     = books.aggregate(s=Sum('read_count'))['s'] or 0
    avg_rating      = books.aggregate(a=Avg('ratings__score'))['a']
    avg_rating      = round(avg_rating, 1) if avg_rating else None

    recent_reviews = Review.objects.filter(book__in=books, status='visible').select_related('user','book').order_by('-created_at')[:5]

    return render(request, 'archives/author_detail.html', {
        'author': author,
        'books': books,
        'liked_ids': liked_ids,
        'categories': cats,
        'other_authors': other,
        'total_downloads': total_downloads,
        'total_reads': total_reads,
        'avg_rating': avg_rating,
        'recent_reviews': recent_reviews,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# ML RECOMMENDATION ENGINE
# Inspired by: Content-Based Filtering (cosine similarity / TF-IDF)
# ═══════════════════════════════════════════════════════════════════════════════

import math

def _book_feature_vector(book, all_categories):
    """
    Build a sparse feature vector for a book.
    Features: one-hot category + language bucket + download popularity bucket.
    This is the 'document vector' in TF-IDF analogy.
    """
    vec = {}
    # Category feature (one-hot)
    if book.category_id:
        vec[f'cat_{book.category_id}'] = 1.0
    # Language feature
    vec[f'lang_{book.language}'] = 1.0
    # Popularity signal (log-scaled download count, like TF weighting)
    if book.download_count > 0:
        vec['popularity'] = math.log1p(book.download_count) / 10.0
    return vec


def _cosine_similarity(vec_a, vec_b):
    """Cosine similarity between two sparse dicts."""
    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in set(vec_a) | set(vec_b))
    mag_a = math.sqrt(sum(v*v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v*v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _content_based_recommendations(user, all_books, all_categories, n=8):
    """
    Content-Based Filtering:
    1. Build user profile = average of feature vectors of user's interacted books.
    2. Compute cosine similarity between user profile and all other books.
    3. Return top-N most similar unseen books.
    """
    interacted_ids = set(
        list(Download.objects.filter(user=user).values_list('book_id', flat=True)) +
        list(Like.objects.filter(user=user).values_list('book_id', flat=True))
    )
    if not interacted_ids:
        return []

    interacted_books = [b for b in all_books if b.id in interacted_ids]
    if not interacted_books:
        return []

    # Build user profile vector (average of book vectors — like averaging TF-IDF vectors)
    profile = {}
    for book in interacted_books:
        bvec = _book_feature_vector(book, all_categories)
        for k, v in bvec.items():
            profile[k] = profile.get(k, 0) + v
    n_interacted = len(interacted_books)
    profile = {k: v / n_interacted for k, v in profile.items()}

    # Score all unseen books
    candidates = []
    for book in all_books:
        if book.id in interacted_ids:
            continue
        bvec = _book_feature_vector(book, all_categories)
        score = _cosine_similarity(profile, bvec)
        if score > 0:
            candidates.append((score, book))

    candidates.sort(key=lambda x: -x[0])
    return [b for _, b in candidates[:n]]


@login_required
def recommendations_view(request):
    all_books = list(Book.objects.filter(is_approved=True).select_related('category').prefetch_related('authors'))
    all_categories = list(Category.objects.all())
    cats = Category.objects.annotate(cnt=Count('books', filter=Q(books__is_approved=True)))

    liked_ids = list(Like.objects.filter(user=request.user).values_list('book_id', flat=True))
    user_books = Book.objects.filter(
        Q(downloads__user=request.user) | Q(likes__user=request.user),
        is_approved=True
    ).distinct()

    # ML model recommendations
    try:
        seed_book = user_books.first()
        if seed_book:
            rec_ids = get_recommendations(seed_book.id, n=8, min_similarity=0.1)
            ml_recs = list(Book.objects.filter(id__in=rec_ids, is_approved=True))
        else:
            ml_recs = []
    except Exception:
        ml_recs = []

    recs = _content_based_recommendations(request.user, all_books, all_categories)

    # Merge ML recs into final list
    seen_ids = {b.id for b in recs}
    for book in ml_recs:
        if book.id not in seen_ids:
            recs.append(book)
            seen_ids.add(book.id)
    recs = recs[:8]

    return render(request, 'archives/recommendations.html', {
        'recs': recs,
        'categories': cats,
        'liked_ids': liked_ids,
        'user_books': user_books,
    })
