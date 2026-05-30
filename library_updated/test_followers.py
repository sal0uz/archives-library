#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'archives_library.settings')
django.setup()

from archives.models import User, Follow

# Get a user
user = User.objects.filter(is_superuser=False).first()
if user:
    print(f"User: {user.username}\n")
    
    # Check followers
    followers = Follow.objects.filter(following=user)
    print(f"Followers count: {followers.count()}")
    for f in followers:
        print(f"  - {f.follower.username}")
    
    # Check following
    following = Follow.objects.filter(follower=user)
    print(f"Following count: {following.count()}")
    for f in following:
        print(f"  - {f.following.username}")
    
    # Test API data
    print(f"\n--- API Response for followers ---")
    followers_data = []
    for f in Follow.objects.filter(following=user).select_related('follower'):
        u = f.follower
        followers_data.append({
            'username': u.username,
            'full_name': u.get_full_name() or u.username,
            'avatar': u.avatar.url if u.avatar else None,
            'first_letter': (u.get_full_name() or u.username)[0].upper()
        })
    print(f"Followers API data: {followers_data}")
    
    print(f"\n--- API Response for following ---")
    following_data = []
    for f in Follow.objects.filter(follower=user).select_related('following'):
        u = f.following
        following_data.append({
            'username': u.username,
            'full_name': u.get_full_name() or u.username,
            'avatar': u.avatar.url if u.avatar else None,
            'first_letter': (u.get_full_name() or u.username)[0].upper()
        })
    print(f"Following API data: {following_data}")
else:
    print("No users found")
