import os
import json
import csv
from typing import Optional

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

MAX_FILE_CHARS = 50000  # Truncate large files to prevent context bloat

def read_file_content(file_path: str, filename: str) -> str:
    """
    Read the contents of a file and return a text representation.
    Supports txt, md, csv, json, common code files, and PDFs.
    Truncates files that exceed MAX_FILE_CHARS.
    """
    if not os.path.exists(file_path):
        return "[Error: File missing on disk]"

    _, ext = os.path.splitext(filename.lower())

    try:
        # 1. Handle PDF
        if ext == ".pdf":
            if not PdfReader:
                return "[Error: PDF parser dependency is not installed]"
            
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                if sum(len(p) for p in text_parts) > MAX_FILE_CHARS:
                    break
            
            full_text = "\n".join(text_parts)
            if not full_text.strip():
                return "[Binary or scanned PDF - text extraction produced no characters]"
            
            return full_text[:MAX_FILE_CHARS]

        # 2. Handle JSON
        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
                pretty_json = json.dumps(data, indent=2)
                return pretty_json[:MAX_FILE_CHARS]

        # 3. Handle CSV
        elif ext == ".csv":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = []
                for i, row in enumerate(reader):
                    rows.append(", ".join(row))
                    if i > 500 or sum(len(r) for r in rows) > MAX_FILE_CHARS:
                        rows.append("[CSV file truncated...]")
                        break
                return "\n".join(rows)

        # 4. Handle text, markdown, and code formats
        elif ext in [".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".yaml", ".yml", ".xml", ".ini", ".cfg", ".sh", ".sql"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(MAX_FILE_CHARS + 100)
                if len(content) > MAX_FILE_CHARS:
                    return content[:MAX_FILE_CHARS] + "\n\n[Content truncated due to size limits...]"
                return content

        # 5. Unsupported binary formats
        else:
            return f"[Binary file type ({ext}) - contents not parsed]"

    except Exception as e:
        return f"[Error parsing file content: {str(e)}]"
