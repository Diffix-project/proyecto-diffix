"""Test end-to-end del script update_docs.py con mock de Gemini.

Ejecutar desde la raiz: python scripts/test_update_docs.py
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

SAMPLE_DIFF = """diff --git a/backend/app/domains/uploads/router.py b/backend/app/domains/uploads/router.py
index abc123..def456 100644
--- a/backend/app/domains/uploads/router.py
+++ b/backend/app/domains/uploads/router.py
@@ -10,6 +10,7 @@
 from app.domains.auth.models import User
 from app.domains.competitors.models import Competitor
 from app.domains.sources.models import CompetitorSource
+from app.core.rate_limit import check_rate_limit
 from app.integrations import storage
 from app.workers.tasks import parse_pdf

diff --git a/frontend/src/features/competitors/CompetitorDetailPage.tsx b/frontend/src/features/competitors/CompetitorDetailPage.tsx
index 111aaa..222bbb 100644
--- a/frontend/src/features/competitors/CompetitorDetailPage.tsx
+++ b/frontend/src/features/competitors/CompetitorDetailPage.tsx
@@ -5,6 +5,7 @@
 import { useParams } from 'react-router-dom'
 import { Card, CardContent, CardHeader } from '@/components/ui/card'
 import { Badge } from '@/components/ui/badge'
+import { ExportButton } from '@/components/ui/export-button'
 import { useCompetitorDetail } from '../api'

 export function CompetitorDetailPage() {

diff --git a/backend/alembic/versions/0003_add_foo.py b/backend/alembic/versions/0003_add_foo.py
new file mode 100644
index 0000000..333ccc
--- /dev/null
+++ b/backend/alembic/versions/0003_add_foo.py
@@ -0,0 +1,20 @@
+\"\"\"add foo table
+
+Revision ID: 0003
+Revises: 0002
+Create Date: 2026-06-08
+\"\"\"
+from alembic import op
+import sqlalchemy as sa
+
+def upgrade():
+    op.create_table('foo',
+        sa.Column('id', sa.Integer(), primary_key=True),
+        sa.Column('name', sa.String(255)),
+    )

diff --git a/docker-compose.yml b/docker-compose.yml
index 888ddd..999eee 100644
--- a/docker-compose.yml
+++ b/docker-compose.yml
@@ -3,6 +3,7 @@
 services:
   api:
     build: ./backend
+    environment:
+      - NEW_VAR=hello
     ports:
       - "8000:8000"
"""

import scripts.update_docs as upd


class TestExtractRelevantDiff(unittest.TestCase):
    def test_arquitectura_solo_frontend(self):
        result = upd.extract_relevant_diff(SAMPLE_DIFF, "docs/arquitectura.md")
        self.assertIn("ExportButton", result)
        self.assertNotIn("check_rate_limit", result)
        self.assertNotIn("add foo table", result)
        self.assertNotIn("NEW_VAR", result)

    def test_endpoints_solo_backend_app(self):
        result = upd.extract_relevant_diff(SAMPLE_DIFF, "docs/endpoints-api.md")
        self.assertIn("check_rate_limit", result)
        self.assertNotIn("ExportButton", result)
        self.assertNotIn("add foo table", result)
        self.assertNotIn("NEW_VAR", result)

    def test_base_datos_solo_alembic(self):
        result = upd.extract_relevant_diff(SAMPLE_DIFF, "docs/base-de-datos.md")
        self.assertIn("add foo table", result)
        self.assertNotIn("check_rate_limit", result)
        self.assertNotIn("ExportButton", result)
        self.assertNotIn("NEW_VAR", result)

    def test_readme_solo_infra(self):
        result = upd.extract_relevant_diff(SAMPLE_DIFF, "README.md")
        self.assertIn("NEW_VAR", result)
        self.assertNotIn("check_rate_limit", result)
        self.assertNotIn("ExportButton", result)
        self.assertNotIn("add foo table", result)

    def test_truncation(self):
        original = upd.MAX_DIFF_CHARS
        upd.MAX_DIFF_CHARS = 50
        try:
            result = upd.extract_relevant_diff(SAMPLE_DIFF, "docs/arquitectura.md")
            self.assertLessEqual(len(result), 50 + 35)
            self.assertIn("truncado", result)
        finally:
            upd.MAX_DIFF_CHARS = original


class TestRetryLogic(unittest.TestCase):
    def setUp(self):
        self.orig_retry_delay = upd.RETRY_BASE_DELAY
        upd.RETRY_BASE_DELAY = 1

    def tearDown(self):
        upd.RETRY_BASE_DELAY = self.orig_retry_delay

    def test_retry_on_429_fail_after_exhaustion(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "429 RESOURCE_EXHAUSTED. {'retryDelay': '1s'}"
        )
        start = time.time()
        with self.assertRaises(Exception):
            upd.generate_with_retry(mock_client, "fake-model", "test prompt", max_retries=3)
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 3.0)
        self.assertEqual(mock_client.models.generate_content.call_count, 3)

    def test_retry_success_on_second_attempt(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "# Doc actualizado"
        mock_client.models.generate_content.side_effect = [
            Exception("429 RESOURCE_EXHAUSTED. {'retryDelay': '1s'}"),
            mock_response,
        ]
        result = upd.generate_with_retry(mock_client, "fake-model", "test prompt", max_retries=3)
        self.assertEqual(result.text, "# Doc actualizado")
        self.assertEqual(mock_client.models.generate_content.call_count, 2)


class TestUpdateDocsPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._backup_docs()

    @classmethod
    def tearDownClass(cls):
        cls._restore_docs()

    @classmethod
    def _backup_docs(cls):
        cls._backups = {}
        for p in ["README.md", "docs/arquitectura.md", "docs/base-de-datos.md", "docs/endpoints-api.md"]:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    cls._backups[p] = f.read()

    @classmethod
    def _restore_docs(cls):
        for p, content in cls._backups.items():
            dir_name = os.path.dirname(p)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)

    def setUp(self):
        self.orig_call_delay = upd.API_CALL_DELAY
        upd.API_CALL_DELAY = 0

    def tearDown(self):
        upd.API_CALL_DELAY = self.orig_call_delay

    def test_pipeline_mocked(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "# Documentacion actualizada por test\n\nContenido generado."
        mock_client.models.generate_content.return_value = mock_response

        changed = [
            "backend/app/domains/uploads/router.py",
            "frontend/src/features/competitors/CompetitorDetailPage.tsx",
            "backend/alembic/versions/0003_add_foo.py",
            "docker-compose.yml",
        ]

        exit_code, errores = upd.update_docs(mock_client, SAMPLE_DIFF, changed)

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(errores), 0)

        # Verificar que se genero cada doc
        self.assertIn("Documentacion actualizada por test", self._read("docs/arquitectura.md"))
        self.assertIn("Documentacion actualizada por test", self._read("docs/endpoints-api.md"))
        self.assertIn("Documentacion actualizada por test", self._read("docs/base-de-datos.md"))
        self.assertIn("Documentacion actualizada por test", self._read("README.md"))

        self.assertEqual(mock_client.models.generate_content.call_count, 4)

    def _read(self, path):
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


if __name__ == "__main__":
    unittest.main()
