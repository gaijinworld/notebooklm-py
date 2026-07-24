#!/usr/bin/env python3
"""
Sync notebooklm-py artifact metadata into Firebase Cloud Firestore for
Project ID: gamified-network-engineer-app
Parent Org: gaijinworld.com
"""

import json
import urllib.error
import urllib.request

PROJECT_ID = "gamified-network-engineer-app"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/artifacts/notebooklm-py"

ARTIFACT_PAYLOAD = {
    "fields": {
        "name": {"stringValue": "notebooklm-py"},
        "title": {"stringValue": "NotebookLM Py"},
        "description": {"stringValue": "Google Gemini NotebookLM Py Integration Artifact"},
        "url": {"stringValue": "http://gaijinworld-local.local/notebooklm-py/"},
        "status": {"stringValue": "active"},
        "projectId": {"stringValue": PROJECT_ID},
        "projectNumber": {"stringValue": "465331311664"},
        "parentOrg": {"stringValue": "gaijinworld.com"},
        "updatedAt": {"timestampValue": "2026-07-23T20:43:00Z"},
    }
}


def main():
    print(f"Syncing notebooklm-py artifact to Firestore project: {PROJECT_ID}...")
    data = json.dumps(ARTIFACT_PAYLOAD).encode("utf-8")
    req = urllib.request.Request(
        FIRESTORE_URL, data=data, headers={"Content-Type": "application/json"}, method="PATCH"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            print("Successfully updated Firestore artifact 'notebooklm-py':")
            print(body)
    except urllib.error.HTTPError as e:
        print(f"HTTP response {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Sync notice: {e}")


if __name__ == "__main__":
    main()
