"""
Hand-labelled test cases for the CodeLens AI evaluation framework.

15 cases covering SQL injection, secrets, N+1 queries, error handling, style,
complexity, concurrency, resource leaks, XSS, nesting, Python gotchas, HTTPS,
magic numbers, divide-by-zero, and unvalidated input.
"""

TEST_CASES = [
    {
        "id": 1,
        "code": '''
def get_user(username):
    query = "SELECT * FROM users WHERE name = '" + username + "'"
    return db.execute(query)
''',
        "language": "python",
        "expected_issues": [
            {"category": "security", "severity": "critical", "description_hint": "SQL injection"},
        ],
    },
    {
        "id": 2,
        "code": '''
API_KEY = "sk-live-abc123xyz789secret"
headers = {"Authorization": f"Bearer {API_KEY}"}
''',
        "language": "python",
        "expected_issues": [
            {"category": "security", "severity": "critical", "description_hint": "hardcoded secret"},
        ],
    },
    {
        "id": 3,
        "code": '''
def list_posts_with_authors():
    posts = Post.objects.all()
    return [{"title": p.title, "author": User.objects.get(id=p.author_id).name} for p in posts]
''',
        "language": "python",
        "expected_issues": [
            {"category": "perf", "severity": "warning", "description_hint": "N+1 query"},
        ],
    },
    {
        "id": 4,
        "code": '''
@app.route("/transfer", methods=["POST"])
def transfer():
    amount = request.form["amount"]
    to_account = request.form["to"]
    process_transfer(amount, to_account)
    return "OK"
''',
        "language": "python",
        "expected_issues": [
            {"category": "security", "severity": "warning", "description_hint": "unvalidated input"},
        ],
    },
    {
        "id": 5,
        "code": '''
import os
import sys
import json
import math
import random
import datetime
import collections

def hello():
    return "world"
''',
        "language": "python",
        "expected_issues": [
            {"category": "style", "severity": "info", "description_hint": "unused imports"},
        ],
    },
    {
        "id": 6,
        "code": '''
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(len(items)):
            if i != j and items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates
''',
        "language": "python",
        "expected_issues": [
            {"category": "complexity", "severity": "warning", "description_hint": "O(n²) nested loop"},
        ],
    },
    {
        "id": 7,
        "code": '''
def fetch_user_data(user_id):
    response = requests.get(f"https://api.example.com/users/{user_id}")
    data = response.json()
    return data["profile"]
''',
        "language": "python",
        "expected_issues": [
            {"category": "bug", "severity": "warning", "description_hint": "missing error handling"},
        ],
    },
    {
        "id": 8,
        "code": '''
import asyncio

counter = 0

async def increment():
    global counter
    temp = counter
    await asyncio.sleep(0)
    counter = temp + 1

async def run_many():
    await asyncio.gather(*[increment() for _ in range(100)])
''',
        "language": "python",
        "expected_issues": [
            {"category": "bug", "severity": "critical", "description_hint": "race condition"},
        ],
    },
    {
        "id": 9,
        "code": '''
def read_config(path):
    f = open(path, "r")
    data = f.read()
    return data
''',
        "language": "python",
        "expected_issues": [
            {"category": "bug", "severity": "warning", "description_hint": "resource leak"},
        ],
    },
    {
        "id": 10,
        "code": '''
function renderComment(comment) {
    document.getElementById("comments").innerHTML = comment.text;
}
''',
        "language": "javascript",
        "expected_issues": [
            {"category": "security", "severity": "critical", "description_hint": "XSS"},
        ],
    },
    {
        "id": 11,
        "code": '''
def process(value):
    if value > 0:
        if value < 100:
            if value % 2 == 0:
                if value > 10:
                    if value < 50:
                        return "small even"
                    else:
                        return "large even"
''',
        "language": "python",
        "expected_issues": [
            {"category": "complexity", "severity": "warning", "description_hint": "deep nesting"},
        ],
    },
    {
        "id": 12,
        "code": '''
def append_item(item, bucket=[]):
    bucket.append(item)
    return bucket
''',
        "language": "python",
        "expected_issues": [
            {"category": "bug", "severity": "critical", "description_hint": "mutable default argument"},
        ],
    },
    {
        "id": 13,
        "code": '''
import requests

def fetch_data(url):
    if url.startswith("http://"):
        return requests.get(url).text
    return requests.get(url).text
''',
        "language": "python",
        "expected_issues": [
            {"category": "security", "severity": "warning", "description_hint": "missing HTTPS"},
        ],
    },
    {
        "id": 14,
        "code": '''
def calculate_discount(price):
    if price > 500:
        return price * 0.85
    elif price > 200:
        return price * 0.92
    return price * 0.97
''',
        "language": "python",
        "expected_issues": [
            {"category": "style", "severity": "info", "description_hint": "magic numbers"},
        ],
    },
    {
        "id": 15,
        "code": '''
def compute_average(numbers):
    total = sum(numbers)
    return total / len(numbers)
''',
        "language": "python",
        "expected_issues": [
            {"category": "bug", "severity": "critical", "description_hint": "divide by zero"},
        ],
    },
]
