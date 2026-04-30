import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
import random
from socketserver import ThreadingMixIn
import string
import threading
from typing import Any
import urllib.parse

from util import db_pool
from util.experiment_times import ExperimentTime
from util.improper_requests import ImproperRequest
from util.requests import Request
from util.task_completion import TaskCompletion

# Heroku serves the website at the port number specified in the environment
# variable $PORT
hostname = "localhost"
if "PORT" not in os.environ:
    os.environ["PORT"] = "34567"

port = os.environ["PORT"]


class HoneySiteRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args):
        self.static_sites_path = "static_sites"
        self.news_site_path = "ai_news_site"
        self.not_found_file = "404.html"
        self.index_file = "index.html"
        self.versions_file = "versions.txt"
        self.robots_txt_file = "robots.txt"
        self.version_name_size = 10
        self.version_names = self.load_version_names()
        self.valid_endpoints = [
            "/fingerprint",
            "/fp",
            "/mouse_movement",
            "/mm",
            "/start",
            "/end",
            "/complete",
            "/complete_update",
        ]
        self.init_mime_type_map()
        self.ongoing_experiments: dict[str, int] = {}
        self.exp_ids: dict[str, int] = {}
        BaseHTTPRequestHandler.__init__(self, *args)

    def init_mime_type_map(self):
        self.mime_type_map = {}
        self.mime_type_map[".jpg"] = "image/jpeg"
        self.mime_type_map[".jpeg"] = "image/jpeg"
        self.mime_type_map[".png"] = "image/png"
        self.mime_type_map[".html"] = "text/html"
        self.mime_type_map[".css"] = "text/css"
        self.mime_type_map[".js"] = "text/javascript"
        self.mime_type_map[".txt"] = "text/plain"

    def load_version_names(self):
        with open(self.versions_file) as f:
            version_names = f.read().splitlines()
        return version_names

    def send_content_headers(self, content_type):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def read_file(self, file_path, binary=False):
        with open(file_path, "rb" if binary else "r") as f:
            content = f.read()
        return content

    def is_valid_request_version(self, request_version):
        return request_version in self.version_names

    def fetch_robots_txt(self):
        return self.read_file(self.robots_txt_file)

    def fetch_image_content(self, path, request_version):
        if self.is_valid_request_version(request_version):
            path = path.replace("/" + request_version, "")

            if path.endswith(".jpg") or path.endswith(".jpeg") or path.endswith(".png"):
                image_file = os.path.join(
                    self.static_sites_path, self.news_site_path, path[1:]
                )

                if os.path.exists(image_file):
                    _, image_extension = os.path.splitext(image_file)
                    self.send_content_headers(self.mime_type_map[image_extension])
                    return self.read_file(image_file, binary=True)

    def fetch_static_content(self, path, request_version):
        is_valid_request = False

        if self.is_valid_request_version(request_version):
            path = path.replace("/" + request_version, "")
            if path == "/":
                path = f"/{self.index_file}"

            path_components = path.split("/")
            if len(path_components) >= 2 and path_components[1] == "completion":
                resource_file = os.path.join(
                    self.static_sites_path,
                    self.news_site_path,
                    "pages",
                    "completion.html",
                )
            else:
                resource_file = os.path.join(
                    self.static_sites_path, self.news_site_path, path[1:]
                )
            _, resource_extension = os.path.splitext(resource_file)

            if os.path.exists(resource_file) and os.path.isfile(resource_file):
                is_valid_request = True
                if path.endswith(".html"):
                    self.send_content_headers(self.mime_type_map[resource_extension])

                    html_content = self.read_file(resource_file)
                    return html_content, is_valid_request

                self.send_content_headers(self.mime_type_map[resource_extension])
                return self.read_file(resource_file), is_valid_request

            # Serve index.html for all subpages
            if (
                len(path_components) > 2
                and path_components[1] == "forums"
                and path_components[2]
                not in [
                    "",
                    "js",
                    "css",
                ]
            ):
                resource_file = os.path.join(
                    self.static_sites_path,
                    self.news_site_path,
                    "pages",
                    "forum_thread",
                )
            else:
                resource_file = os.path.join(
                    self.static_sites_path, self.news_site_path, "pages", path[1:]
                )
            if not path.endswith(".html"):
                resource_file += ".html"
            _, resource_extension = os.path.splitext(resource_file)
            if os.path.exists(resource_file) and os.path.isfile(resource_file):
                is_valid_request = True
                resource_file = os.path.join(
                    self.static_sites_path, self.news_site_path, self.index_file
                )
                if path.endswith(".html"):
                    self.send_content_headers(self.mime_type_map[resource_extension])

                    html_content = self.read_file(resource_file)
                    return html_content, is_valid_request

                self.send_content_headers(self.mime_type_map[resource_extension])
                return self.read_file(resource_file), is_valid_request

        self.send_content_headers(self.mime_type_map[".html"])
        return (
            self.read_file(os.path.join(self.static_sites_path, self.not_found_file)),
            is_valid_request,
        )

    def log_improper_request_helper(
        self, path, req_type, req_headers, req_body, website_version
    ):
        improper_request = ImproperRequest()
        return improper_request.log_improper_request(
            path, req_type, req_headers, req_body, website_version
        )

    def log_request_helper(
        self,
        path,
        req_type,
        req_headers,
        req_body,
        website_version,
        anonymize: bool = False,
    ):
        request = Request()
        return request.log_request(
            path,
            req_type,
            req_headers,
            req_body,
            website_version,
            anonymize=anonymize,
        )

    def log_experiment_time_helper(
        self,
        website_version: str,
        req_id: int,
        is_start: bool,
        exp_id: int | None = None,
        webpage: str | None = None,
    ):
        experiment_time = ExperimentTime()
        if is_start:
            return experiment_time.log_start_experiment_time(website_version, req_id)
        else:
            return experiment_time.log_end_experiment_time(req_id, webpage, exp_id)

    def log_task_completion(self, name, student_id, task, website_version):
        task_completion = TaskCompletion()
        return task_completion.log_task_completion(
            name, student_id, task, website_version
        )

    def log_task_completion_update(
        self, old_name, old_student_id, name, student_id, task, website_version
    ):
        task_completion = TaskCompletion()
        return task_completion.log_task_completion_update(
            old_name, old_student_id, name, student_id, task, website_version
        )

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def generate_random_string(self):
        random_size = 10
        return "".join(
            random.choices(string.ascii_uppercase + string.digits, k=random_size)
        )

    def do_POST(self):
        response_body = ""
        status_code = 200
        exp_id = None  # Store exp_id for /start and /end endpoint response header

        request_version = self.path[: self.version_name_size + 1]
        if len(self.path) > self.version_name_size + 1:
            website_version = request_version[1:]
            endpoint = self.path[self.version_name_size + 1 :]
        else:
            website_version = ""
            endpoint = self.path

        # Read request body once at the beginning
        body_data = b""
        if "Content-Length" in self.headers:
            try:
                content_length = int(self.headers["Content-Length"])
                body_data = self.rfile.read(content_length)
            except (ValueError, OSError) as e:
                logging.error(f"Error reading request body: {e}")
                body_data = b""

        if (
            self.is_valid_request_version(website_version)
            and endpoint in self.valid_endpoints
        ):
            # Valid POST request
            try:
                post_data: dict[str, Any] = json.loads(body_data.decode("utf-8"))

                anonymize = False
                if endpoint == "/complete":
                    # Remove sensitive information
                    anonymize = True
                    for _header in ["Cookie"]:
                        if _header in self.headers:
                            del self.headers[_header]

                req_id = self.log_request_helper(
                    str(self.path),
                    "POST",
                    str(self.headers),
                    json.dumps(post_data),
                    website_version,
                    anonymize,
                )

                if endpoint == "/start":
                    exp_id = self.log_experiment_time_helper(
                        website_version,
                        req_id,
                        True,
                    )
                    with self.server.exp_ids_lock:
                        self.server.exp_ids[website_version] = exp_id
                elif endpoint == "/end":
                    webpage = post_data.get("webpage", "")
                    with self.server.exp_ids_lock:
                        exp_id = self.server.exp_ids.pop(website_version)
                    assert (
                        self.log_experiment_time_helper(
                            website_version, req_id, False, exp_id, webpage
                        )
                        == exp_id
                    )
                # elif endpoint == "/complete":
                #     student_name = post_data.get("studentName", "")
                #     student_id = post_data.get("studentId", "")
                #     task = post_data.get("task", "")
                #     self.log_task_completion(
                #         student_name, student_id, task, website_version
                #     )
                # elif endpoint == "/complete_update":
                #     old_student_id = post_data.get("oldStudentId", "")
                #     student_name = post_data.get("studentName", "")
                #     student_id = post_data.get("studentId", "")
                #     task = post_data.get("task", "")
                #     self.log_task_completion_update(
                #         old_student_id,
                #         student_name,
                #         student_id,
                #         task,
                #         website_version,
                #     )
                response_body = "Success"
            except:
                self.log_improper_request_helper(
                    str(self.path),
                    "POST",
                    str(self.headers),
                    body_data.decode("utf-8", errors="ignore"),
                    website_version,
                )
                response_body = (
                    "Invalid post request to endpoint "
                    + self.path
                    + " with body "
                    + body_data.decode("utf-8", errors="ignore")
                )
                logging.error(response_body)
        else:
            # Invalid POST request
            self.log_improper_request_helper(
                str(self.path),
                "POST",
                str(self.headers),
                body_data.decode("utf-8", errors="ignore"),
                website_version,
            )
            response_body = (
                "Invalid post request to endpoint "
                + self.path
                + " with headers "
                + str(self.headers)
                + " and data "
                + body_data.decode("utf-8", errors="ignore")
            )
            logging.error(response_body)

        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "text/plain")

        if endpoint in ["/start", "/end"]:
            self.send_header("X-Exp-Id", exp_id)

        if len(response_body) > 0:
            response_body = response_body.encode()
            self.send_header("Content-Length", str(len(response_body)))

        self.end_headers()
        self.wfile.write(response_body)

    def do_HEAD(self):
        if len(self.path) > self.version_name_size + 1:
            request_version = self.path[: self.version_name_size + 1]
            website_version = request_version[1:]
        else:
            website_version = ""
        self.log_improper_request_helper(
            str(self.path), "HEAD", str(self.headers), "", website_version
        )
        content = self.fetch_robots_txt()
        self.send_content_headers(self.mime_type_map[".txt"])
        self.wfile.write(bytes(content, encoding="utf8"))

    def do_GET(self):
        if len(self.path) == self.version_name_size + 1:
            self.path = self.path + "/"
        if "?" in self.path:
            components = self.path.split("?")
            self.path = components[0]
            if len(components) > 1:
                params = urllib.parse.parse_qs(components[1])

        # If we need a variable request_version size in the future, can split by /
        # and take the segment at index 1
        request_version = self.path[: self.version_name_size + 1]
        if len(self.path) > self.version_name_size + 1:
            website_version = request_version[1:]
        else:
            website_version = ""

        # Check if path ends with / and is not just the version or root
        if len(self.path) > self.version_name_size + 2 and self.path.endswith("/"):
            # Redirect to URL without trailing slash
            redirect_url = self.path.rstrip("/")
            self.send_response(301)
            self.send_header("Location", redirect_url)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return

        content = self.fetch_image_content(self.path, request_version[1:])

        if content:
            self.wfile.write(content)
        else:
            content, is_valid_request = self.fetch_static_content(
                self.path, website_version
            )
            if is_valid_request:
                self.log_request_helper(
                    str(self.path), "GET", str(self.headers), "", website_version
                )
            else:
                self.log_improper_request_helper(
                    str(self.path), "GET", str(self.headers), "", website_version
                )
            self.wfile.write(bytes(content, encoding="utf8"))


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exp_ids: dict[str, int] = {}
        self.exp_ids_lock = threading.Lock()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, help="Port to run server on")
    args = parser.parse_args()
    if args.port is not None:
        port = args.port

    logging.basicConfig(level=logging.INFO)

    db_pool.init_pool(minconn=1, maxconn=10)

    server = ThreadedHTTPServer(("", int(port)), HoneySiteRequestHandler)
    logging.info("Server running on port " + str(port))

    try:
        server.serve_forever()
    finally:
        db_pool.close_pool()
