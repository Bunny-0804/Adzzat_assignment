#!/usr/bin/env python3
"""
Zero-dependency Python HTTP server serving Azzdat Harbor tasks directly from disk.
Uses exclusively Python standard library modules.
"""
import http.server
import json
import os
from pathlib import Path
import re
import socketserver
import tomllib

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_DIR = BASE_DIR / "tasks"
WEB_DIR = BASE_DIR / "web"

def parse_markdown_sections(md_text: str) -> dict:
    sections = {}
    current_key = "overview"
    current_lines = []

    for line in md_text.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
                current_lines = []
            heading = line[3:].strip().lower()
            if "statement" in heading:
                current_key = "statement"
            elif "environment" in heading:
                current_key = "environment"
            elif "difficulty" in heading:
                current_key = "difficulty_note"
            else:
                current_key = heading.replace(" ", "_")
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections

def load_tasks_from_disk() -> list:
    tasks = []
    if not TASKS_DIR.exists():
        return tasks

    for entry in sorted(os.listdir(TASKS_DIR)):
        task_folder = TASKS_DIR / entry
        if not task_folder.is_dir():
            continue

        toml_path = task_folder / "task.toml"
        md_path = task_folder / "instruction.md"

        if not toml_path.exists() or not md_path.exists():
            continue

        with open(toml_path, "rb") as f:
            toml_data = tomllib.load(f)

        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        sections = parse_markdown_sections(md_content)
        metadata = toml_data.get("metadata", {})
        verifier_timeout = toml_data.get("verifier", {}).get("timeout_sec", 120.0)
        agent_timeout = toml_data.get("agent", {}).get("timeout_sec", 600.0)

        task_info = {
            "id": metadata.get("id", entry),
            "title": metadata.get("title", entry),
            "category": metadata.get("category", "General"),
            "difficulty": metadata.get("difficulty", "medium"),
            "difficulty_note": metadata.get("difficulty_note", ""),
            "statement": sections.get("statement", ""),
            "environment": sections.get("environment", ""),
            "raw_instruction": md_content,
            "verifier_timeout_sec": verifier_timeout,
            "agent_timeout_sec": agent_timeout,
            "timeouts": {
                "verifier_sec": verifier_timeout,
                "agent_sec": agent_timeout
            }
        }
        tasks.append(task_info)

    return tasks

class TaskCatalogHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/tasks":
            tasks = load_tasks_from_disk()
            response_data = json.dumps(tasks, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
            return

        if self.path.startswith("/api/tasks/"):
            task_id = self.path[len("/api/tasks/"):]
            tasks = load_tasks_from_disk()
            matched = next((t for t in tasks if t["id"] == task_id), None)
            if matched:
                response_data = json.dumps(matched, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_data)))
                self.end_headers()
                self.wfile.write(response_data)
            else:
                self.send_error(404, "Task Not Found")
            return

        if self.path == "/":
            self.path = "/index.html"

        return super().do_GET()

if __name__ == "__main__":
    server_address = ("", PORT)
    with socketserver.TCPServer(server_address, TaskCatalogHandler) as httpd:
        print(f"Task Catalog Showcase running at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
