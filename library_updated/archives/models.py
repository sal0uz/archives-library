from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db.models import Avg, Count
import os


# ─── CUSTOM USER ──────────────────────────────────────────────────────────────
class User(AbstractUser):
    STATUS_CHOICES = [
        ('active',  'Active'),
        ('banned',  'Banned'),
        ('suspended', 'Suspended'),
    ]
    bio          = models.TextField(blank=True)
    avatar       = models.ImageField(upload_to='avatars/', blank=True, null=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    ban_until    = models.DateTimeField(blank=True, null=True)
    last_online  = models.DateTimeField(default=timezone.now)
    joined_at    = models.DateTimeField(auto_now_add=True)

    # counters (updated on each relevant action for performance)
    total_downloads = models.PositiveIntegerField(default=0)
    total_reads     = models.PositiveIntegerField(default=0)
    total_uploads   = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'lib_user'

    def __str__(self):
        return self.username

    @property
    def is_online(self):
        from django.conf import settings
        threshold = getattr(settings, 'ONLINE_THRESHOLD', 300)
        return (timezone.now() - self.last_online).total_seconds() < threshold

    @property
    def is_currently_banned(self):
        if self.status == 'banned':
            if self.ban_until is None:
                return True
            return timezone.now() < self.ban_until
        return False

    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None


# ─── CATEGORY ─────────────────────────────────────────────────────────────────
class Category(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    icon       = models.CharField(max_length=10, default='📚')
    slug       = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'lib_category'
        ordering  = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    @property
    def book_count(self):
        return self.books.filter(is_approved=True).count()


# ─── AUTHOR ───────────────────────────────────────────────────────────────────
class Author(models.Model):
    name        = models.CharField(max_length=200)
    nationality = models.CharField(max_length=100, blank=True)
    bio         = models.TextField(blank=True)
    photo       = models.ImageField(upload_to='authors/', blank=True, null=True)
    birth_year  = models.IntegerField(blank=True, null=True)
    death_year  = models.IntegerField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='added_authors')

    class Meta:
        db_table = 'lib_author'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def book_count(self):
        return self.books.filter(is_approved=True).count()

    def photo_url(self):
        if self.photo:
            return self.photo.url
        return None


# ─── BOOK ─────────────────────────────────────────────────────────────────────
class Book(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'), ('ar', 'Arabic'), ('fr', 'French'),
        ('es', 'Spanish'), ('de', 'German'), ('it', 'Italian'),
        ('pt', 'Portuguese'), ('ru', 'Russian'), ('zh', 'Chinese'),
        ('other', 'Other'),
    ]

    title        = models.CharField(max_length=500)
    slug         = models.SlugField(max_length=100, unique=True)
    authors      = models.ManyToManyField(Author, related_name='books', blank=True)
    category     = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='books')
    description  = models.TextField(blank=True)
    cover        = models.ImageField(upload_to='covers/', blank=True, null=True)
    pdf_file     = models.FileField(upload_to='books/', blank=True, null=True)
    language     = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    publisher    = models.CharField(max_length=300, blank=True)
    isbn         = models.CharField(max_length=30, blank=True)
    release_date = models.CharField(max_length=20, blank=True)   # allow BC years
    pages        = models.PositiveIntegerField(blank=True, null=True)
    file_size    = models.CharField(max_length=20, blank=True)   # e.g. "1.2 MB"
    extension    = models.CharField(max_length=10, default='PDF')
    short_link   = models.CharField(max_length=20, blank=True)

    # visibility
    is_approved  = models.BooleanField(default=False)
    is_trending  = models.BooleanField(default=False)
    is_featured  = models.BooleanField(default=False)

    # counters (denormalised for speed)
    download_count = models.PositiveIntegerField(default=0)
    read_count     = models.PositiveIntegerField(default=0)
    like_count     = models.PositiveIntegerField(default=0)

    uploaded_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='uploaded_books')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lib_book'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def cover_url(self):
        if self.cover:
            return self.cover.url
        return None

    def pdf_url(self):
        if self.pdf_file:
            return self.pdf_file.url
        return None

    @property
    def average_rating(self):
        agg = self.ratings.aggregate(avg=Avg('score'))
        val = agg['avg']
        return round(val, 1) if val else 0.0

    @property
    def rating_count(self):
        return self.ratings.count()

    @property
    def rating_distribution(self):
        dist = {}
        for i in range(1, 6):
            dist[i] = self.ratings.filter(score=i).count()
        return dist

    def file_size_display(self):
        if self.pdf_file:
            try:
                size = self.pdf_file.size
                if size < 1024:       return f"{size} B"
                elif size < 1048576:  return f"{size/1024:.1f} KB"
                else:                 return f"{size/1048576:.1f} MB"
            except Exception:
                pass
        return self.file_size or 'N/A'


# ─── RATING ───────────────────────────────────────────────────────────────────
class Rating(models.Model):
    book       = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='ratings')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    score      = models.PositiveSmallIntegerField()   # 1-5
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lib_rating'
        unique_together = ('book', 'user')

    def __str__(self):
        return f"{self.user} → {self.book} : {self.score}★"


# ─── REVIEW / COMMENT ─────────────────────────────────────────────────────────
class Review(models.Model):
    STATUS_CHOICES = [
        ('visible',  'Visible'),
        ('flagged',  'Flagged'),
        ('removed',  'Removed'),
    ]
    book       = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    body       = models.TextField()
    likes      = models.ManyToManyField(User, related_name='liked_reviews', blank=True)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='visible')
    created_at = models.DateTimeField(auto_now_add=True)
    moderated_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='moderated_reviews')
    moderated_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lib_review'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} on {self.book}"

    @property
    def like_count(self):
        return self.likes.count()


# ─── QUOTE ────────────────────────────────────────────────────────────────────
class Quote(models.Model):
    book       = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='quotes')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quotes')
    body       = models.TextField()
    likes      = models.ManyToManyField(User, related_name='liked_quotes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lib_quote'
        ordering = ['-created_at']

    @property
    def like_count(self):
        return self.likes.count()


# ─── LIKE (book ↔ user) ───────────────────────────────────────────────────────
class Like(models.Model):
    book       = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='likes')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_books')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lib_like'
        unique_together = ('book', 'user')


# ─── DOWNLOAD LOG ─────────────────────────────────────────────────────────────
class Download(models.Model):
    book       = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='downloads')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lib_download'
        unique_together = ('book', 'user')


# ─── READ LOG ─────────────────────────────────────────────────────────────────
class ReadLog(models.Model):
    book      = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='read_logs')
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_logs')
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lib_readlog'
        unique_together = ('book', 'user')


# ─── COMMUNITY POST ───────────────────────────────────────────────────────────
class CommunityPost(models.Model):
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    topic      = models.CharField(max_length=300)
    body       = models.TextField()
    likes      = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lib_communitypost'
        ordering = ['-created_at']

    def __str__(self):
        return self.topic

    @property
    def like_count(self):
        return self.likes.count()


class PostComment(models.Model):
    post       = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='post_comments')
    author     = models.ForeignKey(User, on_delete=models.CASCADE)
    body       = models.TextField()
    likes      = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lib_postcomment'
        ordering = ['created_at']

    @property
    def like_count(self):
        return self.likes.count()


# ─── SITE STATS (aggregate row updated daily by management command) ────────────
class SiteStats(models.Model):
    date              = models.DateField(unique=True)
    visitors          = models.PositiveIntegerField(default=0)
    daily_searches    = models.PositiveIntegerField(default=0)
    total_downloads   = models.PositiveIntegerField(default=0)
    total_reads       = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'lib_sitestats'


# ─── FOLLOW (user ↔ user) ─────────────────────────────────────────────────────
class Follow(models.Model):
    follower   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lib_follow'
        unique_together = ('follower', 'following')
