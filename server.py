import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8000
DATA_FILE = Path(__file__).with_name("tasks.txt")
ALLOWED_PRIORITIES = {"low", "normal", "high"}


def load_tasks():
    if not DATA_FILE.exists():
        return {}, 1

    try:
        raw_tasks = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}, 1

    tasks = {}
    next_id = 1

    for item in raw_tasks:
        if not isinstance(item, dict):
            continue

        task_id = item.get("id")
        title = item.get("title")
        priority = item.get("priority")
        is_done = item.get("isDone")

        if (
            isinstance(task_id, int)
            and isinstance(title, str)
            and priority in ALLOWED_PRIORITIES
            and isinstance(is_done, bool)
        ):
            tasks[task_id] = {
                "id": task_id,
                "title": title,
                "priority": priority,
                "isDone": is_done,
            }
            next_id = max(next_id, task_id + 1)

    return tasks, next_id


TASKS, NEXT_ID = load_tasks()


def save_tasks():
    ordered_tasks = [TASKS[task_id] for task_id in sorted(TASKS)]
    DATA_FILE.write_text(
        json.dumps(ordered_tasks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class TodoHandler(BaseHTTPRequestHandler):
    server_version = "TodoServer/1.0"

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            return self._send_json(
                {
                    "message": "Todo API is running",
                    "endpoints": [
                        "GET /tasks",
                        "POST /tasks",
                        "POST /tasks/{id}/complete",
                    ],
                }
            )

        if parsed.path == "/tasks":
            tasks = [TASKS[task_id] for task_id in sorted(TASKS)]
            return self._send_json(tasks)

        return self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/tasks":
            return self._create_task()

        if parsed.path.startswith("/tasks/") and parsed.path.endswith("/complete"):
            return self._complete_task(parsed.path)

        return self._send_json({"error": "Not found"}, status=404)

    def _create_task(self):
        global NEXT_ID

        try:
            payload = self._read_json()
        except ValueError as error:
            return self._send_json({"error": str(error)}, status=400)

        title = payload.get("title")
        priority = payload.get("priority")

        if not isinstance(title, str) or not title.strip():
            return self._send_json({"error": "Field 'title' is required"}, status=400)

        if priority not in ALLOWED_PRIORITIES:
            return self._send_json(
                {"error": "Field 'priority' must be one of: low, normal, high"},
                status=400,
            )

        task = {
            "id": NEXT_ID,
            "title": title.strip(),
            "priority": priority,
            "isDone": False,
        }

        TASKS[NEXT_ID] = task
        NEXT_ID += 1
        save_tasks()
        return self._send_json(task, status=201)

    def _complete_task(self, path):
        parts = path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "tasks" or parts[2] != "complete":
            return self._send_json({"error": "Not found"}, status=404)

        try:
            task_id = int(parts[1])
        except ValueError:
            return self._send_json({"error": "Not found"}, status=404)

        task = TASKS.get(task_id)
        if task is None:
            return self._send_json({"error": "Task not found"}, status=404)

        task["isDone"] = True
        save_tasks()

        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_json(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")

        if not raw_body:
            raise ValueError("Request body is required")

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as error:
            raise ValueError("Invalid JSON body") from error

        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")

        return payload

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format_string, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), TodoHandler)
    print(f"Todo API is running at http://{HOST}:{PORT}")
    server.serve_forever()
