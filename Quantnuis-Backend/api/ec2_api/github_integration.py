#!/usr/bin/env python3
"""
================================================================================
                    GITHUB INTEGRATION
================================================================================

Push approved annotations to GitHub repository.

================================================================================
"""

import os
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx


GITHUB_API_URL = "https://api.github.com"
REPO_OWNER = "ElMonstroDelBrest"
REPO_NAME = "Quantnuis-Web-Site"
BRANCH = "main"


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN")


async def push_approved_annotation(
    audio_path: str,
    annotations_data: list,
    model_type: str,
    user_email: str,
    request_id: int
) -> dict:
    """
    Push approved annotation files to GitHub.

    Creates a commit with:
    - The audio file
    - The annotations CSV

    Files are stored in: Quantnuis-Backend/data/{model_type}/contributions/{timestamp}_{request_id}/
    """
    token = get_github_token()
    if not token:
        return {"success": False, "error": "GITHUB_TOKEN not configured"}

    # Prepare paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_request{request_id}"
    base_path = f"Quantnuis-Backend/data/{model_type}/contributions/{folder_name}"

    # Read audio file
    audio_file = Path(audio_path)
    if not audio_file.exists():
        return {"success": False, "error": f"Audio file not found: {audio_path}"}

    audio_content = audio_file.read_bytes()
    audio_b64 = base64.b64encode(audio_content).decode('utf-8')
    audio_filename = f"audio{audio_file.suffix}"

    # Create CSV content
    csv_lines = ["Start,End,Label,Reliability,Note"]
    for ann in annotations_data:
        note = ann.get('note', '').replace('"', '""')
        csv_lines.append(f"{ann['start']},{ann['end']},{ann['label']},{ann['reliability']},\"{note}\"")
    csv_content = "\n".join(csv_lines)
    csv_b64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')

    # Create metadata file
    metadata = {
        "submitted_by": user_email,
        "request_id": request_id,
        "model_type": model_type,
        "annotation_count": len(annotations_data),
        "approved_at": datetime.now().isoformat(),
        "original_filename": audio_file.name
    }
    metadata_b64 = base64.b64encode(json.dumps(metadata, indent=2).encode('utf-8')).decode('utf-8')

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    async with httpx.AsyncClient() as client:
        try:
            # Get the current commit SHA of the branch
            ref_response = await client.get(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/ref/heads/{BRANCH}",
                headers=headers
            )
            if ref_response.status_code != 200:
                return {"success": False, "error": f"Failed to get branch ref: {ref_response.text}"}

            current_sha = ref_response.json()["object"]["sha"]

            # Get the current tree
            commit_response = await client.get(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/commits/{current_sha}",
                headers=headers
            )
            if commit_response.status_code != 200:
                return {"success": False, "error": f"Failed to get commit: {commit_response.text}"}

            base_tree_sha = commit_response.json()["tree"]["sha"]

            # Create blobs for each file
            blobs = []

            # Audio blob
            audio_blob_response = await client.post(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs",
                headers=headers,
                json={"content": audio_b64, "encoding": "base64"}
            )
            if audio_blob_response.status_code != 201:
                return {"success": False, "error": f"Failed to create audio blob: {audio_blob_response.text}"}
            blobs.append({
                "path": f"{base_path}/{audio_filename}",
                "mode": "100644",
                "type": "blob",
                "sha": audio_blob_response.json()["sha"]
            })

            # CSV blob
            csv_blob_response = await client.post(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs",
                headers=headers,
                json={"content": csv_b64, "encoding": "base64"}
            )
            if csv_blob_response.status_code != 201:
                return {"success": False, "error": f"Failed to create CSV blob: {csv_blob_response.text}"}
            blobs.append({
                "path": f"{base_path}/annotations.csv",
                "mode": "100644",
                "type": "blob",
                "sha": csv_blob_response.json()["sha"]
            })

            # Metadata blob
            meta_blob_response = await client.post(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs",
                headers=headers,
                json={"content": metadata_b64, "encoding": "base64"}
            )
            if meta_blob_response.status_code != 201:
                return {"success": False, "error": f"Failed to create metadata blob: {meta_blob_response.text}"}
            blobs.append({
                "path": f"{base_path}/metadata.json",
                "mode": "100644",
                "type": "blob",
                "sha": meta_blob_response.json()["sha"]
            })

            # Create new tree
            tree_response = await client.post(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/trees",
                headers=headers,
                json={"base_tree": base_tree_sha, "tree": blobs}
            )
            if tree_response.status_code != 201:
                return {"success": False, "error": f"Failed to create tree: {tree_response.text}"}

            new_tree_sha = tree_response.json()["sha"]

            # Create commit
            commit_message = f"Add approved annotation: {model_type} (request #{request_id})\n\nSubmitted by: {user_email}\nAnnotations: {len(annotations_data)}"
            commit_create_response = await client.post(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/commits",
                headers=headers,
                json={
                    "message": commit_message,
                    "tree": new_tree_sha,
                    "parents": [current_sha]
                }
            )
            if commit_create_response.status_code != 201:
                return {"success": False, "error": f"Failed to create commit: {commit_create_response.text}"}

            new_commit_sha = commit_create_response.json()["sha"]

            # Update branch reference
            update_ref_response = await client.patch(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{BRANCH}",
                headers=headers,
                json={"sha": new_commit_sha}
            )
            if update_ref_response.status_code != 200:
                return {"success": False, "error": f"Failed to update ref: {update_ref_response.text}"}

            return {
                "success": True,
                "commit_sha": new_commit_sha,
                "files_pushed": [
                    f"{base_path}/{audio_filename}",
                    f"{base_path}/annotations.csv",
                    f"{base_path}/metadata.json"
                ],
                "message": f"Pushed to GitHub: {base_path}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
