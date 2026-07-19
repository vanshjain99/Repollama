from __future__ import annotations
import pytest
from repollama.engines.security_auditor import SecurityAuditor
from repollama.engines.performance_auditor import PerformanceAuditor


def test_security_auditor_scan_secrets() -> None:
    auditor = SecurityAuditor()
    
    file_contents = {
        "src/config.py": (
            "import os\n"
            "api_key = \"supersecretvalue123\"\n" # flag
            "API_KEY = 'anothersecretvalue'\n"  # flag
            "password = os.getenv('DB_PASSWORD')\n" # no flag
            "token = os.environ.get('TOKEN')\n"     # no flag
            "empty_token = ''\n"                   # no flag
            "dummy_pw = 'todo'\n"                  # no flag
            "normal_var = 'hello world'\n"         # no flag
            "secret_key_var: str = 'my-super-secret-key-1'\n" # flag
            "if password == '12345':\n"            # no flag (comparison)
            "    pass"
        )
    }
    
    flags = auditor.scan_secrets(file_contents)
    
    # We expect 3 secrets flagged: api_key, API_KEY, secret_key_var
    assert len(flags) == 3
    
    # Check that they match the expected line numbers
    lines = [f["line"] for f in flags]
    assert 2 in lines
    assert 3 in lines
    assert 9 in lines
    
    for flag in flags:
        assert flag["file"] == "src/config.py"
        assert flag["issue"] == "Hardcoded secret detected"
        assert flag["severity"] == "High"


def test_security_auditor_scan_weak_crypto() -> None:
    auditor = SecurityAuditor()
    
    ast_data = [
        {
            "file_path": "src/hash_utils.py",
            "language": "python",
            "imports": ["from hashlib import md5, sha1", "import jwt"],
            "classes": [
                {"name": "MD5Hasher", "start_line": 5, "end_line": 8}
            ],
            "functions": [
                {"name": "use_sha1_hash", "start_line": 10, "end_line": 12}
            ]
        },
        {
            "file_path": "src/secure_jwt.py",
            "language": "python",
            "imports": ["import jwt", "import os"], # has key management (os)
            "classes": [],
            "functions": [
                {"name": "sign_hs256_token", "start_line": 4, "end_line": 8}
            ]
        },
        {
            "file_path": "src/insecure_jwt.py",
            "language": "python",
            "imports": ["import jwt"], # no key management (os/dotenv/etc)
            "classes": [],
            "functions": [
                {"name": "sign_hs256_token", "start_line": 4, "end_line": 8}
            ]
        }
    ]
    
    flags = auditor.scan_weak_crypto(ast_data)
    
    # Expected flags:
    # 1. src/hash_utils.py: md5 import (line 1)
    # 2. src/hash_utils.py: sha1 import (line 1) (since md5 and sha1 are in the same import or processed)
    # 3. src/hash_utils.py: MD5Hasher class (line 5)
    # 4. src/hash_utils.py: use_sha1_hash function (line 10)
    # 5. src/insecure_jwt.py: sign_hs256_token function (line 4) (no key management)
    # Note: src/secure_jwt.py has os imported, so hs256 function should NOT flag.
    
    # Let's count flags for hash_utils.py
    hash_utils_flags = [f for f in flags if f["file"] == "src/hash_utils.py"]
    assert len(hash_utils_flags) >= 3
    
    # Ensure MD5 and SHA1 warnings are captured
    issues = [f["issue"] for f in hash_utils_flags]
    assert any("MD5/SHA1" in issue for issue in issues)
    assert any("MD5Hasher" in issue for issue in issues)
    assert any("use_sha1_hash" in issue for issue in issues)
    
    # Ensure insecure JWT flags HS256 usage
    insecure_jwt_flags = [f for f in flags if f["file"] == "src/insecure_jwt.py"]
    assert len(insecure_jwt_flags) == 1
    assert "HS256" in insecure_jwt_flags[0]["issue"]
    
    # Ensure secure JWT is not flagged for HS256
    secure_jwt_flags = [f for f in flags if f["file"] == "src/secure_jwt.py"]
    assert len(secure_jwt_flags) == 0


def test_performance_auditor_bloated_functions() -> None:
    # We pass empty file contents because we're testing line span from AST metadata only (no N+1 loop check here)
    auditor = PerformanceAuditor()
    
    ast_data = [
        {
            "file_path": "src/utils.py",
            "language": "python",
            "imports": [],
            "classes": [],
            "functions": [
                {"name": "small_func", "start_line": 5, "end_line": 20}, # 16 lines
                {"name": "bloated_func", "start_line": 25, "end_line": 150} # 126 lines -> flag
            ]
        }
    ]
    
    flags = auditor.detect_anti_patterns(ast_data)
    
    assert len(flags) == 1
    assert flags[0]["file"] == "src/utils.py"
    assert "Bloated function" in flags[0]["issue"]
    assert flags[0]["target"] == "bloated_func"
    assert flags[0]["target_function"] == "bloated_func"
    assert flags[0]["severity"] == "Low"


def test_performance_auditor_n1_queries_python() -> None:
    # Python code contents with ORM calls inside loops vs outside
    file_contents = {
        "src/users.py": (
            "def process_users():\n"
            "    users = User.select()\n" # outside loop, ok
            "    for user in users:\n"
            "        profile = Profile.find(user.id)\n" # inside loop, flag!
            "        print(profile)\n"
        ),
        "src/posts.py": (
            "def process_posts():\n"
            "    posts = Post.select()\n"
            "    for post in posts:\n"
            "        # Just print, no query\n"
            "        print(post.title)\n"
        ),
        "src/async_tasks.py": (
            "async def run_tasks():\n"
            "    while True:\n"
            "        await fetch_data()\n" # await in loop, flag!
        )
    }
    
    auditor = PerformanceAuditor(file_contents=file_contents)
    
    ast_data = [
        {
            "file_path": "src/users.py",
            "language": "python",
            "functions": [
                {"name": "process_users", "start_line": 1, "end_line": 5}
            ]
        },
        {
            "file_path": "src/posts.py",
            "language": "python",
            "functions": [
                {"name": "process_posts", "start_line": 1, "end_line": 5}
            ]
        },
        {
            "file_path": "src/async_tasks.py",
            "language": "python",
            "functions": [
                {"name": "run_tasks", "start_line": 1, "end_line": 3}
            ]
        }
    ]
    
    flags = auditor.detect_anti_patterns(ast_data)
    
    # We expect flags for users.py and async_tasks.py, but not posts.py
    n1_flags = [f for f in flags if "N+1" in f["issue"]]
    assert len(n1_flags) == 2
    
    flagged_files = [f["file"] for f in n1_flags]
    assert "src/users.py" in flagged_files
    assert "src/async_tasks.py" in flagged_files
    assert "src/posts.py" not in flagged_files


def test_performance_auditor_n1_queries_javascript() -> None:
    # JS/TS code contents with loops
    file_contents = {
        "src/users.js": (
            "function processUsers() {\n"
            "  const users = db.select();\n"
            "  users.forEach(user => {\n"
            "    const profile = db.find(user.id); // inside loop, flag!\n"
            "  });\n"
            "}\n"
        ),
        "src/posts.ts": (
            "async function processPosts() {\n"
            "  for (const post of posts) {\n"
            "    await fetch('url/' + post.id); // await in loop, flag!\n"
            "  }\n"
            "}\n"
        )
    }
    
    auditor = PerformanceAuditor(file_contents=file_contents)
    
    ast_data = [
        {
            "file_path": "src/users.js",
            "language": "javascript",
            "functions": [
                {"name": "processUsers", "start_line": 1, "end_line": 6}
            ]
        },
        {
            "file_path": "src/posts.ts",
            "language": "typescript",
            "functions": [
                {"name": "processPosts", "start_line": 1, "end_line": 5}
            ]
        }
    ]
    
    flags = auditor.detect_anti_patterns(ast_data)
    
    n1_flags = [f for f in flags if "N+1" in f["issue"]]
    assert len(n1_flags) == 2
    assert n1_flags[0]["file"] == "src/users.js"
    assert n1_flags[1]["file"] == "src/posts.ts"
    assert n1_flags[0]["target_function"] == "processUsers"
    assert n1_flags[1]["target_function"] == "processPosts"


def test_performance_auditor_n1_queries_await_outside_loop() -> None:
    file_contents = {
        "src/await_query.py": (
            "async def get_details(user_id):\n"
            "    user = await db.find(user_id)\n" # contains find + await, flag!
            "    return user\n"
        ),
        "src/await_no_query.py": (
            "async def get_details(user_id):\n"
            "    user = await get_user(user_id)\n" # contains await but no query/find/select, ok
            "    return user\n"
        )
    }
    
    auditor = PerformanceAuditor(file_contents=file_contents)
    
    ast_data = [
        {
            "file_path": "src/await_query.py",
            "language": "python",
            "functions": [
                {"name": "get_details", "start_line": 1, "end_line": 3}
            ]
        },
        {
            "file_path": "src/await_no_query.py",
            "language": "python",
            "functions": [
                {"name": "get_details", "start_line": 1, "end_line": 3}
            ]
        }
    ]
    
    flags = auditor.detect_anti_patterns(ast_data)
    n1_flags = [f for f in flags if "N+1" in f["issue"]]
    assert len(n1_flags) == 1
    assert n1_flags[0]["file"] == "src/await_query.py"
    assert n1_flags[0]["target_function"] == "get_details"
    assert n1_flags[0]["severity"] == "Medium"
