import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day1ScaffoldTest(unittest.TestCase):
    def test_required_project_files_exist(self):
        expected_files = [
            ".env.example",
            ".gitignore",
            "README.md",
            "docker-compose.yml",
            "backend/Dockerfile",
            "backend/pyproject.toml",
            "backend/requirements.txt",
            "backend/app/main.py",
            "backend/app/core/config.py",
            "backend/app/db/session.py",
            "frontend/Dockerfile",
            "frontend/package.json",
            "frontend/app/layout.tsx",
            "frontend/app/page.tsx",
            "frontend/app/globals.css",
            "frontend/components/Dashboard.tsx",
            "frontend/lib/dashboard-data.ts",
            "docs/day1-project-initialization.md",
        ]

        missing = [path for path in expected_files if not (ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_backend_exposes_health_and_database_health(self):
        main_py = read_text("backend/app/main.py")

        self.assertIn('@app.get("/health")', main_py)
        self.assertIn('@app.get("/db/health")', main_py)
        self.assertIn("check_database_connection", main_py)

    def test_docker_compose_wires_day1_services(self):
        compose = read_text("docker-compose.yml")

        required_fragments = [
            "pgvector/pgvector:pg16",
            "context: ./backend",
            "context: ./frontend",
            '"${POSTGRES_PORT:-5432}:5432"',
            '"${BACKEND_PORT:-8000}:8000"',
            '"${FRONTEND_PORT:-3000}:3000"',
            "condition: service_healthy",
            "postgres_data:",
        ]
        missing = [fragment for fragment in required_fragments if fragment not in compose]

        self.assertEqual(missing, [])

    def test_env_example_contains_day1_runtime_variables(self):
        env_example = read_text(".env.example")

        expected_keys = [
            "POSTGRES_DB=",
            "POSTGRES_USER=",
            "POSTGRES_PASSWORD=",
            "POSTGRES_PORT=",
            "BACKEND_PORT=",
            "FRONTEND_PORT=",
            "DATABASE_URL=",
            "JWT_SECRET_KEY=",
            "OPENAI_API_KEY=",
            "STORAGE_DIR=",
            "NEXT_PUBLIC_API_BASE_URL=",
        ]
        missing = [key for key in expected_keys if key not in env_example]

        self.assertEqual(missing, [])

    def test_frontend_declares_next_app_and_dashboard(self):
        package_json = json.loads(read_text("frontend/package.json"))
        page_tsx = read_text("frontend/app/page.tsx")
        dashboard_tsx = read_text("frontend/components/Dashboard.tsx")

        self.assertIn("next", package_json["dependencies"])
        self.assertIn("react", package_json["dependencies"])
        self.assertIn("getStoredSession", page_tsx)
        self.assertIn("Midori", dashboard_tsx)
        self.assertIn("企业支持智能体", dashboard_tsx)
        self.assertIn("企业支持智能体", dashboard_tsx)


if __name__ == "__main__":
    unittest.main()
