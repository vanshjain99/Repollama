from __future__ import annotations
import re
from typing import Any


class SecurityAuditor:
    """Scans repository files and AST metadata for security vulnerabilities.

    Specifically, flags hardcoded secrets (API keys, passwords, tokens) and usage of
    weak cryptographic functions/algorithms (MD5, SHA-1, HS256).
    """

    def scan_secrets(self, file_contents: dict[str, str]) -> list[dict[str, Any]]:
        """Scan raw file contents for potential hardcoded secrets using regex.

        Args:
            file_contents: A dictionary mapping file paths to their raw string content.

        Returns:
            A list of flag dictionaries representing detected secrets:
            [{"file": "src/config.py", "issue": "Hardcoded secret detected", "severity": "High", "line": 12}]
        """
        flags: list[dict[str, Any]] = []

        # Matches assignments like: name = "secret" or name: str = "secret"
        # Using negative lookbehind/lookahead for equals to prevent matching '==' or '!='
        secret_pattern = re.compile(
            r'(?i)\b\w*(api_key|secret|password|token)\w*\b(?:\s*:\s*[\w\[\]]+)?\s*(?<![=!<>])=(?![=])\s*([\'"])(.*?)\2'
        )

        placeholders = {
            "your_api_key", "your_secret", "your_password", "your_token",
            "api_key_here", "secret_here", "password_here", "token_here",
            "your-api-key", "your-secret", "your-password", "your-token",
            "<api_key>", "<secret>", "<password>", "<token>",
            "placeholder", "todo", "xxxxxx", "none", "null", "false", "true"
        }

        for file_path, content in file_contents.items():
            lines = content.splitlines()
            for line_idx, line in enumerate(lines, start=1):
                # Ignore common false-positives (e.g. getenv, environ, process.env, config retrievals)
                if any(fp in line for fp in ["getenv(", "environ.get(", "environ[", "process.env", "config.get(", "config("]):
                    continue

                match = secret_pattern.search(line)
                if match:
                    secret_val = match.group(3)
                    # Skip empty, white-space only, or too short strings (e.g. dummy values)
                    if not secret_val.strip() or len(secret_val) < 5:
                        continue

                    lower_val = secret_val.lower()
                    # Skip common placeholder names or expressions containing templating indicators
                    if lower_val in placeholders or any(p in lower_val for p in ["<", ">", "{", "}"]):
                        continue

                    flags.append({
                        "file": file_path,
                        "issue": "Hardcoded secret detected",
                        "severity": "High",
                        "line": line_idx
                    })

        return flags

    def scan_weak_crypto(self, ast_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Analyze AST metadata (imports, functions, classes) for weak hashing algorithms.

        Specifically scans for MD5/SHA-1 usage, or HS256 without environment/config management.

        Args:
            ast_data: A list of dicts, each representing file AST metadata.

        Returns:
            A list of flag dictionaries representing weak crypto occurrences:
            [{"file": "src/auth.py", "issue": "Weak cryptographic hashing (MD5/SHA1) detected", "severity": "Medium", "line": 1}]
        """
        flags: list[dict[str, Any]] = []

        for file_ast in ast_data:
            file_path = file_ast.get("file_path", "")
            imports = file_ast.get("imports", [])
            classes = file_ast.get("classes", [])
            functions = file_ast.get("functions", [])

            # Check if any import suggests proper config/secrets/environment management is present in the file
            has_key_management = any(
                any(k in imp.lower() for k in ["os", "dotenv", "environ", "config", "settings", "kms", "vault"])
                for imp in imports
            )

            # 1. Scan import statements
            for imp in imports:
                imp_lower = imp.lower()
                if "md5" in imp_lower or "sha1" in imp_lower:
                    flags.append({
                        "file": file_path,
                        "issue": "Weak cryptographic hashing (MD5/SHA1) detected",
                        "severity": "Medium",
                        "line": 1
                    })
                if "hs256" in imp_lower and not has_key_management:
                    flags.append({
                        "file": file_path,
                        "issue": "Usage of HS256 without proper key management",
                        "severity": "Medium",
                        "line": 1
                    })

            # 2. Scan class definitions
            for cls in classes:
                cls_name = cls.get("name", "")
                cls_lower = cls_name.lower()
                start_line = cls.get("start_line", 1)
                if "md5" in cls_lower or "sha1" in cls_lower:
                    flags.append({
                        "file": file_path,
                        "issue": f"Weak cryptographic hashing referenced in class '{cls_name}'",
                        "severity": "Medium",
                        "line": start_line
                    })
                if "hs256" in cls_lower and not has_key_management:
                    flags.append({
                        "file": file_path,
                        "issue": f"Usage of HS256 without proper key management in class '{cls_name}'",
                        "severity": "Medium",
                        "line": start_line
                    })

            # 3. Scan function definitions
            for func in functions:
                func_name = func.get("name", "")
                func_lower = func_name.lower()
                start_line = func.get("start_line", 1)
                if "md5" in func_lower or "sha1" in func_lower:
                    flags.append({
                        "file": file_path,
                        "issue": f"Weak cryptographic hashing referenced in function '{func_name}'",
                        "severity": "Medium",
                        "line": start_line
                    })
                if "hs256" in func_lower and not has_key_management:
                    flags.append({
                        "file": file_path,
                        "issue": f"Usage of HS256 without proper key management in function '{func_name}'",
                        "severity": "Medium",
                        "line": start_line
                    })

        return flags
