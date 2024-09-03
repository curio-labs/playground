import datetime

REPLICATION_PERIODS = [
    (datetime.time(0, 0), datetime.time(0, 30)),
    (datetime.time(6, 0), datetime.time(6, 30)),
    (datetime.time(12, 0), datetime.time(12, 30)),
    (datetime.time(18, 0), datetime.time(18, 30)),
]
READABLE_PERIODS = [
    ("00:00", "00:30"),
    ("06:00", "06:30"),
    ("12:00", "12:30"),
    ("18:00", "18:30"),
]

REPLICATING_HTML_MSG = f"""
    <p>The database is currently replicating. Please try again later.</p>
    <p>Replication occurs daily during the following periods:</p>
    <ul>
        <li>01:00-01:30</li>
        <li>07:00-07:30</li>
        <li>13:00-13:30</li>
        <li>19:00-19:30</li>
    </ul>
"""
STORY_ATTRIBUTES_UI = [
    {"name": "title", "default": True},
    {"name": "text", "default": True},
    {"name": "published_at", "default": False},
    {"name": "publication", "default": False},
    {"name": "author", "default": False},
    {"name": "type", "default": False},
    {"name": "classification", "default": False},
]
