#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'archives_library.settings')
django.setup()

from django.test import Client
import json

client = Client()

# Test followers API
print("Testing /api/followers/salma/")
response = client.get('/api/followers/salma/')
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type')}")
try:
    data = json.loads(response.content)
    print(f"Response: {json.dumps(data, indent=2)}")
except:
    print(f"Response text: {response.content}")

print("\n" + "="*60)

# Test following API
print("Testing /api/following/salma/")
response = client.get('/api/following/salma/')
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type')}")
try:
    data = json.loads(response.content)
    print(f"Response: {json.dumps(data, indent=2)}")
except:
    print(f"Response text: {response.content}")
