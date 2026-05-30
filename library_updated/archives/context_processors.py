from .models import Category, Author
from django.db.models import Count, Q


def global_context(request):
    """Inject categories and authors into every template context."""
    if not request.user.is_authenticated:
        return {}
    cats = Category.objects.annotate(
        cnt=Count('books', filter=Q(books__is_approved=True))
    ).order_by('name')
    all_authors = Author.objects.order_by('name')
    all_cats    = cats  # alias used in upload modal
    return {
        'all_categories': all_cats,
        'all_authors':    all_authors,
    }
