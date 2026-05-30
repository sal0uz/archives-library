
"""
archives/recommendation_service.py
─────────────────────────────────────────────────────────────────────────────
Service de recommandation personnalisé pour la bibliothèque.
- Content-based filtering (similarity entre livres)
"""

import os
import joblib
from django.conf import settings

# Chemin vers les modèles sauvegardés
MODELS_DIR = os.path.join(settings.BASE_DIR, 'recommendation_models')

# ─── Chargement paresseux (au premier appel) ──────────────────────────────────
_cache = {}

def _load(name):
    if name not in _cache:
        _cache[name] = joblib.load(os.path.join(MODELS_DIR, f'{name}.pkl'))
    return _cache[name]


def get_recommendations(book_id: int, user=None, max_results: int = 4, min_similarity: float = 0.5) -> list[int]:
    """
    Retourne les book_ids recommandés pour le livre donné.

    Args:
        book_id: ID du livre pour lequel trouver des recommandations
        user: User object (optionnel) - non utilisé dans la version actuelle
        max_results: Nombre maximum de recommandations (défaut: 4)
        min_similarity: Seuil de similarité minimum (défaut: 0.5 = 50%)

    Usage:
        from archives.recommendation_service import get_recommendations
        recs = get_recommendations(book.id, user=request.user, max_results=6)
        recommended_books = Book.objects.filter(id__in=recs, is_approved=True)
    """
    try:
        cosine_sim      = _load('cosine_sim')
        book_id_to_idx  = _load('book_id_to_idx')
        idx_to_book_id  = _load('idx_to_book_id')
        df_books        = _load('df_books')

        all_book_ids = df_books['book_id'].tolist()

        # ─ Scores Content-Based (similarité de contenu)
        if book_id in book_id_to_idx:
            idx = book_id_to_idx[book_id]
            scores = [
                (int(idx_to_book_id[i]), float(cosine_sim[idx][i]))
                for i in range(len(cosine_sim[idx]))
                if int(idx_to_book_id[i]) != book_id
            ]
        else:
            return []

        if not scores:
            return []

        scores.sort(key=lambda x: x[1], reverse=True)
        top_score = scores[0][1]

        # Si le meilleur livre n'a pas assez de similarité, ne rien recommander.
        if top_score < min_similarity:
            return []

        # Ne conserver que les recommandations assez proches
        # On prend seulement les livres qui ont au moins 60 % du score du meilleur.
        threshold = max(min_similarity, top_score * 0.6)
        selected = [pair for pair in scores if pair[1] >= threshold]

        if not selected:
            return []

        return [bid for bid, _ in selected[:max_results]]

    except Exception as e:
        print(f"[Recommendation] Erreur : {e}")
        return []
