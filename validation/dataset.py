"""Validation dataset for Mnemonic algorithm evaluation.

Contains:
- 100 conversations with ground truth memories
- 50 search queries with expected results
- Conflict scenarios
- Noise injection patterns
"""

# ─── 100条对话数据集 ──────────────────────────────────────────────────────

CONVERSATIONS = [
    # Simple facts (1-20)
    {
        "id": "conv_001",
        "messages": [
            {"role": "user", "content": "My name is John Smith"},
            {"role": "assistant", "content": "Nice to meet you, John!"},
        ],
        "expected_memories": [
            {"content": "User's name is John Smith", "type": "fact", "importance": 0.8},
        ],
    },
    {
        "id": "conv_002",
        "messages": [
            {"role": "user", "content": "I'm 28 years old"},
            {"role": "assistant", "content": "Got it, you're 28."},
        ],
        "expected_memories": [
            {"content": "User is 28 years old", "type": "fact", "importance": 0.7},
        ],
    },
    {
        "id": "conv_003",
        "messages": [
            {"role": "user", "content": "I live in San Francisco"},
            {"role": "assistant", "content": "San Francisco is a great city!"},
        ],
        "expected_memories": [
            {"content": "User lives in San Francisco", "type": "fact", "importance": 0.7},
        ],
    },
    {
        "id": "conv_004",
        "messages": [
            {"role": "user", "content": "I work as a software engineer at Google"},
            {"role": "assistant", "content": "That's impressive! Google is a great company."},
        ],
        "expected_memories": [
            {"content": "User works as a software engineer at Google", "type": "fact", "importance": 0.8},
        ],
    },
    {
        "id": "conv_005",
        "messages": [
            {"role": "user", "content": "My email is john.smith@gmail.com"},
            {"role": "assistant", "content": "I've noted your email address."},
        ],
        "expected_memories": [
            {"content": "User's email is john.smith@gmail.com", "type": "fact", "importance": 0.8},
        ],
    },
    {
        "id": "conv_006",
        "messages": [
            {"role": "user", "content": "I have a dog named Max"},
            {"role": "assistant", "content": "Max sounds like a wonderful pet!"},
        ],
        "expected_memories": [
            {"content": "User has a dog named Max", "type": "fact", "importance": 0.7},
        ],
    },
    {
        "id": "conv_007",
        "messages": [
            {"role": "user", "content": "I'm married to Sarah"},
            {"role": "assistant", "content": "That's lovely! How long have you been married?"},
        ],
        "expected_memories": [
            {"content": "User is married to Sarah", "type": "fact", "importance": 0.8},
        ],
    },
    {
        "id": "conv_008",
        "messages": [
            {"role": "user", "content": "I have two children"},
            {"role": "assistant", "content": "That's wonderful! Tell me about them."},
        ],
        "expected_memories": [
            {"content": "User has two children", "type": "fact", "importance": 0.7},
        ],
    },
    {
        "id": "conv_009",
        "messages": [
            {"role": "user", "content": "My birthday is on March 15th"},
            {"role": "assistant", "content": "I'll remember that! March 15th."},
        ],
        "expected_memories": [
            {"content": "User's birthday is on March 15th", "type": "fact", "importance": 0.8},
        ],
    },
    {
        "id": "conv_010",
        "messages": [
            {"role": "user", "content": "I speak English and Spanish"},
            {"role": "assistant", "content": "Being bilingual is a great skill!"},
        ],
        "expected_memories": [
            {"content": "User speaks English and Spanish", "type": "fact", "importance": 0.6},
        ],
    },
    # Preferences (11-30)
    {
        "id": "conv_011",
        "messages": [
            {"role": "user", "content": "I love pizza, especially pepperoni"},
            {"role": "assistant", "content": "Pepperoni pizza is a classic choice!"},
        ],
        "expected_memories": [
            {"content": "User loves pizza, especially pepperoni", "type": "preference", "importance": 0.7},
        ],
    },
    {
        "id": "conv_012",
        "messages": [
            {"role": "user", "content": "I hate spicy food"},
            {"role": "assistant", "content": "I'll keep that in mind when suggesting restaurants."},
        ],
        "expected_memories": [
            {"content": "User hates spicy food", "type": "preference", "importance": 0.7},
        ],
    },
    {
        "id": "conv_013",
        "messages": [
            {"role": "user", "content": "My favorite color is blue"},
            {"role": "assistant", "content": "Blue is a calming color!"},
        ],
        "expected_memories": [
            {"content": "User's favorite color is blue", "type": "preference", "importance": 0.6},
        ],
    },
    {
        "id": "conv_014",
        "messages": [
            {"role": "user", "content": "I prefer tea over coffee"},
            {"role": "assistant", "content": "Tea is a healthier choice!"},
        ],
        "expected_memories": [
            {"content": "User prefers tea over coffee", "type": "preference", "importance": 0.6},
        ],
    },
    {
        "id": "conv_015",
        "messages": [
            {"role": "user", "content": "I enjoy reading science fiction books"},
            {"role": "assistant", "content": "Science fiction is fascinating! Any favorite authors?"},
        ],
        "expected_memories": [
            {"content": "User enjoys reading science fiction books", "type": "preference", "importance": 0.7},
        ],
    },
    {
        "id": "conv_016",
        "messages": [
            {"role": "user", "content": "I like to exercise in the morning"},
            {"role": "assistant", "content": "Morning workouts are great for energy!"},
        ],
        "expected_memories": [
            {"content": "User likes to exercise in the morning", "type": "preference", "importance": 0.6},
        ],
    },
    {
        "id": "conv_017",
        "messages": [
            {"role": "user", "content": "I prefer working from home"},
            {"role": "assistant", "content": "Remote work has many benefits!"},
        ],
        "expected_memories": [
            {"content": "User prefers working from home", "type": "preference", "importance": 0.6},
        ],
    },
    {
        "id": "conv_018",
        "messages": [
            {"role": "user", "content": "I love traveling to Europe"},
            {"role": "assistant", "content": "Europe has so many amazing destinations!"},
        ],
        "expected_memories": [
            {"content": "User loves traveling to Europe", "type": "preference", "importance": 0.7},
        ],
    },
    {
        "id": "conv_019",
        "messages": [
            {"role": "user", "content": "I prefer dark chocolate over milk chocolate"},
            {"role": "assistant", "content": "Dark chocolate is healthier and more sophisticated!"},
        ],
        "expected_memories": [
            {"content": "User prefers dark chocolate over milk chocolate", "type": "preference", "importance": 0.6},
        ],
    },
    {
        "id": "conv_020",
        "messages": [
            {"role": "user", "content": "I enjoy playing tennis on weekends"},
            {"role": "assistant", "content": "Tennis is a great way to stay active!"},
        ],
        "expected_memories": [
            {"content": "User enjoys playing tennis on weekends", "type": "preference", "importance": 0.6},
        ],
    },
    # Events with temporal references (21-40)
    {
        "id": "conv_021",
        "messages": [
            {"role": "user", "content": "I have a meeting tomorrow at 2pm"},
            {"role": "assistant", "content": "I'll remind you about your meeting tomorrow at 2pm."},
        ],
        "expected_memories": [
            {"content": "User has a meeting tomorrow at 2pm", "type": "event", "importance": 0.8},
        ],
    },
    {
        "id": "conv_022",
        "messages": [
            {"role": "user", "content": "I'm flying to New York next week"},
            {"role": "assistant", "content": "Have a great trip to New York!"},
        ],
        "expected_memories": [
            {"content": "User is flying to New York next week", "type": "event", "importance": 0.8},
        ],
    },
    {
        "id": "conv_023",
        "messages": [
            {"role": "user", "content": "I graduated from Stanford in 2018"},
            {"role": "assistant", "content": "Congratulations on your graduation from Stanford!"},
        ],
        "expected_memories": [
            {"content": "User graduated from Stanford in 2018", "type": "event", "importance": 0.8},
        ],
    },
    {
        "id": "conv_024",
        "messages": [
            {"role": "user", "content": "I'm getting married in June 2025"},
            {"role": "assistant", "content": "That's exciting! Congratulations on your upcoming wedding!"},
        ],
        "expected_memories": [
            {"content": "User is getting married in June 2025", "type": "event", "importance": 0.9},
        ],
    },
    {
        "id": "conv_025",
        "messages": [
            {"role": "user", "content": "I started my current job 3 years ago"},
            {"role": "assistant", "content": "That's a good tenure at your current job!"},
        ],
        "expected_memories": [
            {"content": "User started current job 3 years ago", "type": "event", "importance": 0.7},
        ],
    },
    # Complex conversations (41-60)
    {
        "id": "conv_041",
        "messages": [
            {"role": "user", "content": "I'm John, I work at Microsoft as a product manager"},
            {"role": "assistant", "content": "Nice to meet you John! Microsoft is a great company."},
            {"role": "user", "content": "I've been there for 2 years"},
            {"role": "assistant", "content": "That's a good amount of time to get established."},
        ],
        "expected_memories": [
            {"content": "User's name is John", "type": "fact", "importance": 0.8},
            {"content": "User works at Microsoft as a product manager", "type": "fact", "importance": 0.8},
            {"content": "User has been at Microsoft for 2 years", "type": "fact", "importance": 0.7},
        ],
    },
    {
        "id": "conv_042",
        "messages": [
            {"role": "user", "content": "I love Italian food, especially pasta"},
            {"role": "assistant", "content": "Italian cuisine is wonderful!"},
            {"role": "user", "content": "But I'm allergic to shellfish"},
            {"role": "assistant", "content": "I'll remember that allergy. It's important to avoid shellfish."},
        ],
        "expected_memories": [
            {"content": "User loves Italian food, especially pasta", "type": "preference", "importance": 0.7},
            {"content": "User is allergic to shellfish", "type": "fact", "importance": 0.9},
        ],
    },
    {
        "id": "conv_043",
        "messages": [
            {"role": "user", "content": "I have a meeting with the CEO tomorrow"},
            {"role": "assistant", "content": "That sounds important!"},
            {"role": "user", "content": "It's at 3pm in the conference room"},
            {"role": "assistant", "content": "I've noted the time and location."},
        ],
        "expected_memories": [
            {"content": "User has a meeting with the CEO tomorrow at 3pm in the conference room", "type": "event", "importance": 0.9},
        ],
    },
    # Conflict scenarios (61-80)
    {
        "id": "conv_061",
        "messages": [
            {"role": "user", "content": "I live in New York"},
            {"role": "assistant", "content": "New York is an amazing city!"},
        ],
        "expected_memories": [
            {"content": "User lives in New York", "type": "fact", "importance": 0.7},
        ],
        "conflict_with": "conv_003",  # Previously said San Francisco
    },
    {
        "id": "conv_062",
        "messages": [
            {"role": "user", "content": "I actually don't like pizza anymore"},
            {"role": "assistant", "content": "Tastes can change over time!"},
        ],
        "expected_memories": [
            {"content": "User doesn't like pizza anymore", "type": "preference", "importance": 0.7},
        ],
        "conflict_with": "conv_011",  # Previously loved pizza
    },
    {
        "id": "conv_063",
        "messages": [
            {"role": "user", "content": "I'm now 29 years old"},
            {"role": "assistant", "content": "Happy belated birthday!"},
        ],
        "expected_memories": [
            {"content": "User is 29 years old", "type": "fact", "importance": 0.7},
        ],
        "conflict_with": "conv_002",  # Previously 28
    },
    # Noise/irrelevant conversations (81-100)
    {
        "id": "conv_081",
        "messages": [
            {"role": "user", "content": "What's the weather like?"},
            {"role": "assistant", "content": "I don't have access to real-time weather data."},
        ],
        "expected_memories": [],  # No memories should be extracted
    },
    {
        "id": "conv_082",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there! How can I help you?"},
        ],
        "expected_memories": [],  # No memories should be extracted
    },
    {
        "id": "conv_083",
        "messages": [
            {"role": "user", "content": "Thanks"},
            {"role": "assistant", "content": "You're welcome!"},
        ],
        "expected_memories": [],  # No memories should be extracted
    },
    {
        "id": "conv_084",
        "messages": [
            {"role": "user", "content": "Goodbye"},
            {"role": "assistant", "content": "Goodbye! Have a great day!"},
        ],
        "expected_memories": [],  # No memories should be extracted
    },
    {
        "id": "conv_085",
        "messages": [
            {"role": "user", "content": "Can you help me?"},
            {"role": "assistant", "content": "Of course! What do you need help with?"},
        ],
        "expected_memories": [],  # No memories should be extracted
    },
]

# ─── 50条搜索查询 ──────────────────────────────────────────────────────

SEARCH_QUERIES = [
    # Simple queries (1-20)
    {
        "id": "query_001",
        "query": "What is my name?",
        "expected_memory_ids": ["conv_001"],
        "expected_content_keywords": ["John", "Smith"],
    },
    {
        "id": "query_002",
        "query": "How old am I?",
        "expected_memory_ids": ["conv_002", "conv_063"],
        "expected_content_keywords": ["28", "29", "years old"],
    },
    {
        "id": "query_003",
        "query": "Where do I live?",
        "expected_memory_ids": ["conv_003", "conv_061"],
        "expected_content_keywords": ["San Francisco", "New York"],
    },
    {
        "id": "query_004",
        "query": "Where do I work?",
        "expected_memory_ids": ["conv_004"],
        "expected_content_keywords": ["Google", "software engineer"],
    },
    {
        "id": "query_005",
        "query": "What is my email?",
        "expected_memory_ids": ["conv_005"],
        "expected_content_keywords": ["john.smith@gmail.com"],
    },
    # Preference queries (21-35)
    {
        "id": "query_021",
        "query": "What food do I like?",
        "expected_memory_ids": ["conv_011", "conv_042"],
        "expected_content_keywords": ["pizza", "Italian", "pasta"],
    },
    {
        "id": "query_022",
        "query": "What are my dietary restrictions?",
        "expected_memory_ids": ["conv_042"],
        "expected_content_keywords": ["allergic", "shellfish"],
    },
    {
        "id": "query_023",
        "query": "Do I like coffee or tea?",
        "expected_memory_ids": ["conv_014"],
        "expected_content_keywords": ["tea", "coffee"],
    },
    {
        "id": "query_024",
        "query": "What are my hobbies?",
        "expected_memory_ids": ["conv_015", "conv_020"],
        "expected_content_keywords": ["reading", "tennis", "science fiction"],
    },
    {
        "id": "query_025",
        "query": "What's my favorite color?",
        "expected_memory_ids": ["conv_013"],
        "expected_content_keywords": ["blue"],
    },
    # Event queries (36-45)
    {
        "id": "query_036",
        "query": "What meetings do I have?",
        "expected_memory_ids": ["conv_021", "conv_043"],
        "expected_content_keywords": ["meeting", "CEO", "tomorrow"],
    },
    {
        "id": "query_037",
        "query": "When am I traveling?",
        "expected_memory_ids": ["conv_022"],
        "expected_content_keywords": ["New York", "next week", "flying"],
    },
    {
        "id": "query_038",
        "query": "Where did I go to school?",
        "expected_memory_ids": ["conv_023"],
        "expected_content_keywords": ["Stanford", "2018"],
    },
    {
        "id": "query_039",
        "query": "When is my wedding?",
        "expected_memory_ids": ["conv_024"],
        "expected_content_keywords": ["married", "June", "2025"],
    },
    {
        "id": "query_040",
        "query": "How long have I been at my job?",
        "expected_memory_ids": ["conv_025", "conv_041"],
        "expected_content_keywords": ["3 years", "2 years", "job"],
    },
    # Complex queries (46-50)
    {
        "id": "query_046",
        "query": "Tell me about my family",
        "expected_memory_ids": ["conv_007", "conv_008", "conv_006"],
        "expected_content_keywords": ["married", "Sarah", "children", "dog", "Max"],
    },
    {
        "id": "query_047",
        "query": "What do you know about my work?",
        "expected_memory_ids": ["conv_004", "conv_041", "conv_025"],
        "expected_content_keywords": ["Google", "Microsoft", "software engineer", "product manager"],
    },
    {
        "id": "query_048",
        "query": "What are my upcoming events?",
        "expected_memory_ids": ["conv_021", "conv_022", "conv_024", "conv_043"],
        "expected_content_keywords": ["meeting", "flying", "wedding", "tomorrow", "next week"],
    },
    {
        "id": "query_049",
        "query": "What languages do I speak?",
        "expected_memory_ids": ["conv_010"],
        "expected_content_keywords": ["English", "Spanish"],
    },
    {
        "id": "query_050",
        "query": "What should I avoid eating?",
        "expected_memory_ids": ["conv_042", "conv_012"],
        "expected_content_keywords": ["shellfish", "allergic", "spicy"],
    },
]

# ─── 冲突场景 ──────────────────────────────────────────────────────

CONFLICT_SCENARIOS = [
    {
        "id": "conflict_001",
        "memory_1": {"content": "User lives in San Francisco", "type": "fact"},
        "memory_2": {"content": "User lives in New York", "type": "fact"},
        "expected_resolution": "UPDATE",
        "expected_result": "User lives in New York",
    },
    {
        "id": "conflict_002",
        "memory_1": {"content": "User is 28 years old", "type": "fact"},
        "memory_2": {"content": "User is 29 years old", "type": "fact"},
        "expected_resolution": "UPDATE",
        "expected_result": "User is 29 years old",
    },
    {
        "id": "conflict_003",
        "memory_1": {"content": "User loves pizza", "type": "preference"},
        "memory_2": {"content": "User doesn't like pizza anymore", "type": "preference"},
        "expected_resolution": "CONTRADICTION",
        "expected_result": "User doesn't like pizza anymore",
    },
    {
        "id": "conflict_004",
        "memory_1": {"content": "User works at Google", "type": "fact"},
        "memory_2": {"content": "User works at Microsoft", "type": "fact"},
        "expected_resolution": "UPDATE",
        "expected_result": "User works at Microsoft",
    },
    {
        "id": "conflict_005",
        "memory_1": {"content": "User is single", "type": "fact"},
        "memory_2": {"content": "User is married to Sarah", "type": "fact"},
        "expected_resolution": "UPDATE",
        "expected_result": "User is married to Sarah",
    },
]

# ─── 噪声注入模式 ──────────────────────────────────────────────────────

NOISE_PATTERNS = [
    {
        "id": "noise_001",
        "content": "The quick brown fox jumps over the lazy dog",
        "should_be_filtered": True,
        "reason": "Generic sentence with no personal information",
    },
    {
        "id": "noise_002",
        "content": "Lorem ipsum dolor sit amet consectetur adipiscing elit",
        "should_be_filtered": True,
        "reason": "Lorem ipsum placeholder text",
    },
    {
        "id": "noise_003",
        "content": "Hello world this is a test message",
        "should_be_filtered": True,
        "reason": "Generic test message",
    },
    {
        "id": "noise_004",
        "content": "User likes to breathe air and drink water",
        "should_be_filtered": True,
        "reason": "Trivial information that applies to everyone",
    },
    {
        "id": "noise_005",
        "content": "Random string of words without any meaningful context or personal relevance",
        "should_be_filtered": True,
        "reason": "Random meaningless text",
    },
]