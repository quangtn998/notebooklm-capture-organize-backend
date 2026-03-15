from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import load_settings
from app.http_helpers import reset_rate_limit_buckets
from app.main import create_app


class OwnedMvpContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        reset_rate_limit_buckets()
        settings = replace(
            load_settings(),
            backend_base_url="http://127.0.0.1:8787",
            database_path=Path(self.tempdir.name) / "test.sqlite3",
            session_secret="test-session-secret",
            public_support_email="support@notebooklmcaptureorganize.test",
            request_log_enabled=False,
            auth_rate_limit_window_seconds=60,
            auth_rate_limit_max_attempts=50,
        )
        self.client_context = TestClient(create_app(settings))
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_auth_and_password_flow(self) -> None:
        register = self.client.post(
            "/rest/v1/users",
            json={"Email": "owner@example.com", "Password": "password123"},
        )
        self.assertEqual(register.status_code, 200)
        self.assertTrue(register.json()["data"]["Success"])

        status = self.client.get("/rest/v1/auth/is-logged-in")
        self.assertTrue(status.json()["data"]["IsLoggedIn"])

        info = self.client.get("/rest/v1/users/info")
        payload = info.json()["data"]
        self.assertEqual(payload["Email"], "owner@example.com")
        self.assertTrue(payload["HasPassword"])
        self.assertEqual(payload["AuthProvider"], "password")

        password_update = self.client.post(
            "/rest/v1/users/update-password",
            json={"OldPassword": "password123", "NewPassword": "password456"},
        )
        self.assertTrue(password_update.json()["data"]["Success"])

        logout = self.client.get("/rest/v1/auth/logout")
        self.assertTrue(logout.json()["data"]["Success"])
        self.assertFalse(self.client.get("/rest/v1/auth/is-logged-in").json()["data"]["IsLoggedIn"])

        bad_login = self.client.post(
            "/rest/v1/auth/login",
            json={"Email": "owner@example.com", "Password": "wrong-password"},
        )
        self.assertFalse(bad_login.json()["data"]["Success"])

        login = self.client.post(
            "/rest/v1/auth/login",
            json={"Email": "owner@example.com", "Password": "password456"},
        )
        self.assertTrue(login.json()["data"]["Success"])

    def test_folders_notebooks_and_captures_flow(self) -> None:
        self._register_and_login()

        parent = self.client.post("/rest/v1/folders", json={"Title": "Projects"}).json()["data"]
        child = self.client.post(
            "/rest/v1/folders",
            json={"Title": "Active", "ParentFolderID": parent["FolderID"]},
        ).json()["data"]
        self.assertTrue(parent["Success"])
        self.assertTrue(child["Success"])

        rename = self.client.put(
            "/rest/v1/folders/update-title",
            json={"FolderID": child["FolderID"], "Title": "Archived"},
        ).json()["data"]
        self.assertEqual(rename["Folder"]["Title"], "Archived")

        move = self.client.put(
            "/rest/v1/folders/update-parent-id",
            json={"FolderID": child["FolderID"], "ParentFolderID": None},
        ).json()["data"]
        self.assertEqual(move["Folder"]["ParentFolderID"], "")

        notebook = self.client.post(
            "/rest/v1/notebooks",
            json={
                "ExternalID": "nb-001",
                "Title": "Knowledge Base",
                "FolderID": parent["FolderID"],
                "Emoji": "📘",
                "SourceCount": 2,
            },
        ).json()["data"]
        self.assertTrue(notebook["Success"])
        self.assertEqual(notebook["Notebook"]["FolderID"], parent["FolderID"])

        mapped = self.client.put(
            "/rest/v1/notebooks/update-folder",
            json={"ExternalID": "nb-001", "FolderID": child["FolderID"]},
        ).json()["data"]
        self.assertEqual(mapped["Notebook"]["FolderID"], child["FolderID"])

        second = self.client.post(
            "/rest/v1/notebooks",
            json={"ExternalID": "nb-002", "Title": "Reading Queue"},
        ).json()["data"]
        bulk = self.client.put(
            "/rest/v1/notebooks/bulk-update-folder",
            json={"ExternalIDs": ["nb-001", "nb-002", "nb-404"], "FolderID": parent["FolderID"]},
        ).json()["data"]
        self.assertEqual(bulk["UpdatedCount"], 2)
        self.assertEqual(bulk["FailedCount"], 1)
        self.assertEqual(second["Notebook"]["ExternalID"], "nb-002")

        notebooks = self.client.get("/rest/v1/notebooks").json()["data"]["Notebooks"]
        self.assertEqual({item["ExternalID"] for item in notebooks}, {"nb-001", "nb-002"})

        capture = self.client.post(
            "/rest/v1/captures",
            json={
                "NotebookID": "nb-001",
                "Title": "Imported article",
                "SourceURL": "https://example.com/article",
                "SourceType": "URL",
                "Note": "keep this",
                "RawPayload": {"stage": "capture"},
            },
        ).json()["data"]
        captures = self.client.get("/rest/v1/captures").json()["data"]["Captures"]
        self.assertTrue(capture["Success"])
        self.assertEqual(len(captures), 1)
        self.assertEqual(captures[0]["notebook_external_id"], "nb-001")

        delete_notebook = self.client.delete("/rest/v1/notebooks/by-external-id/nb-002").json()["data"]
        delete_folder = self.client.delete(f"/rest/v1/folders/by-id/{child['FolderID']}").json()["data"]
        self.assertTrue(delete_notebook["Success"])
        self.assertTrue(delete_folder["Success"])

    def test_extension_info_and_deferred_contract(self) -> None:
        info = self.client.get("/rest/v1/extension/info")
        payload = info.json()["data"]
        self.assertEqual(payload["Mode"], "notebooklm-companion")
        self.assertIn("capture-metadata", payload["OwnedFeatures"])
        self.assertIn("billing", payload["DeferredFeatures"])
        self.assertEqual(payload["DeploymentProvider"], "render")
        self.assertEqual(payload["OptionalHostAccessMode"], "pinned-hosts")
        self.assertEqual(payload["SupportURL"], "http://127.0.0.1:8787/support")
        self.assertEqual(payload["PrivacyPolicyURL"], "http://127.0.0.1:8787/privacy-policy")

        deferred = self.client.get("/rest/v1/payments/users/plan")
        deferred_payload = deferred.json()["data"]
        self.assertEqual(deferred_payload["FeatureStatus"], "deferred")
        self.assertEqual(deferred_payload["DeferredFeature"], "billing")
        self.assertEqual(deferred.headers["X-Request-ID"] != "", True)
        self.assertEqual(deferred.headers["Cache-Control"], "no-store")

        document = self.client.post("/rest/v1/sources/get-document")
        self.assertEqual(document.status_code, 200)
        self.assertEqual(document.headers["X-Feature-Status"], "deferred")
        self.assertEqual(document.headers["X-Deferred-Feature"], "source-document-mirror")

    def test_public_support_and_privacy_routes(self) -> None:
        support = self.client.get("/support")
        self.assertEqual(support.status_code, 200)
        self.assertIn("NotebookLM Capture Organize", support.text)
        self.assertIn("support@notebooklmcaptureorganize.test", support.text)

        support_request = self.client.post(
            "/support/requests",
            json={
                "email": "reader@example.com",
                "subject": "Need help with organize",
                "message": "The folder tree works. I need export guidance.",
            },
        )
        payload = support_request.json()["data"]
        self.assertTrue(payload["Success"])
        self.assertGreater(payload["RequestID"], 0)

        invalid = self.client.post(
            "/support/requests",
            json={"email": "bad-email", "subject": "", "message": ""},
        )
        self.assertFalse(invalid.json()["data"]["Success"])

        privacy = self.client.get("/privacy-policy")
        reviewer_notes = self.client.get("/reviewer-notes")
        self.assertEqual(privacy.status_code, 200)
        self.assertEqual(reviewer_notes.status_code, 200)
        self.assertIn("Privacy Policy", privacy.text)
        self.assertIn("Reviewer Notes", reviewer_notes.text)

    def _register_and_login(self) -> None:
        response = self.client.post(
            "/rest/v1/users",
            json={"Email": "organizer@example.com", "Password": "password123"},
        )
        self.assertTrue(response.json()["data"]["Success"])


if __name__ == "__main__":
    unittest.main()
