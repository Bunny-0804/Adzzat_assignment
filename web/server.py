#!/usr/bin/env python3
import http.server
import socketserver
import os
import json
import re

try:
    import tomllib
except ImportError:
    import tomli as tomllib

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(BASE_DIR, "tasks")
WEB_DIR = os.path.join(BASE_DIR, "web")

def parse_markdown_sections(md_text):
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

def load_tasks_from_disk():
    tasks = []
    if not os.path.exists(TASKS_DIR):
        return tasks

    for entry in sorted(os.listdir(TASKS_DIR)):
        task_folder = os.path.join(TASKS_DIR, entry)
        if not os.path.isdir(task_folder):
            continue

        toml_path = os.path.join(task_folder, "task.toml")
        md_path = os.path.join(task_folder, "instruction.md")

        if not os.path.exists(toml_path) or not os.path.exists(md_path):
            continue

        with open(toml_path, "rb") as f:
            toml_data = tomllib.load(f)

        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        sections = parse_markdown_sections(md_content)
        metadata = toml_data.get("metadata", {})

        task_info = {
            "id": metadata.get("id", entry),
            "title": metadata.get("title", entry),
            "category": metadata.get("category", "General"),
            "difficulty": metadata.get("difficulty", "medium"),
            "difficulty_note": metadata.get("difficulty_note", ""),
            "statement": sections.get("statement", ""),
            "environment": sections.get("environment", ""),
            "raw_instruction": md_content,
            "verifier_timeout_sec": toml_data.get("verifier", {}).get("timeout_sec", 120.0),
            "agent_timeout_sec": toml_data.get("agent", {}).get("timeout_sec", 600.0),
        }
        tasks.append(task_info)

    return tasks

class TaskCatalogHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

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
            self.send_header("Access-Control-Allow-Origin", "*")
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
                self.send_header("Access-Control-Allow-Origin", "*")
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
