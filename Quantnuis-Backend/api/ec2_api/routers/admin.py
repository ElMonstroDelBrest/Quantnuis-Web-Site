#!/usr/bin/env python3
"""
================================================================================
                    EC2 API - ADMIN ROUTER
================================================================================

Admin endpoints for managing users and annotation requests.

================================================================================
"""

import os
import io
import json
import tempfile
from datetime import datetime
from contextlib import redirect_stdout

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db, User, AnnotationRequest, AnnotationRequestStatus
from database.schemas import AnnotationRequestReview
from ..dependencies import get_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


# ==============================================================================
# ANNOTATION REQUESTS MANAGEMENT
# ==============================================================================

@router.get("/annotation-requests")
async def get_pending_annotation_requests(
    status_filter: str = "pending",
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get annotation requests (admin only).

    Parameters:
        status_filter: Filter by status ("pending", "approved", "rejected", "all")
    """
    query = db.query(AnnotationRequest)

    if status_filter != "all":
        query = query.filter(AnnotationRequest.status == status_filter)

    requests = query.order_by(AnnotationRequest.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "filename": r.filename,
            "model_type": r.model_type,
            "status": r.status,
            "annotation_count": r.annotation_count,
            "total_duration": r.total_duration,
            "created_at": r.created_at,
            "reviewed_at": r.reviewed_at,
            "admin_note": r.admin_note,
            "submitted_by_email": r.submitted_by.email if r.submitted_by else None,
            "reviewed_by_email": r.reviewed_by.email if r.reviewed_by else None
        }
        for r in requests
    ]


@router.get("/annotation-requests/stats")
async def get_annotation_requests_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get annotation request statistics (admin only)."""
    pending = db.query(AnnotationRequest).filter(
        AnnotationRequest.status == AnnotationRequestStatus.PENDING
    ).count()

    approved = db.query(AnnotationRequest).filter(
        AnnotationRequest.status == AnnotationRequestStatus.APPROVED
    ).count()

    rejected = db.query(AnnotationRequest).filter(
        AnnotationRequest.status == AnnotationRequestStatus.REJECTED
    ).count()

    total_annotations = sum(r.annotation_count for r in db.query(AnnotationRequest).filter(
        AnnotationRequest.status == AnnotationRequestStatus.APPROVED
    ).all())

    return {
        "total_pending": pending,
        "total_approved": approved,
        "total_rejected": rejected,
        "total_annotations_integrated": total_annotations
    }


@router.get("/annotation-requests/{request_id}")
async def get_annotation_request_details(
    request_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get annotation request details (admin only)."""
    request = db.query(AnnotationRequest).filter(
        AnnotationRequest.id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Demande non trouvee")

    return {
        "id": request.id,
        "filename": request.filename,
        "audio_path": request.audio_path,
        "model_type": request.model_type,
        "status": request.status,
        "annotations": json.loads(request.annotations_data),
        "annotation_count": request.annotation_count,
        "total_duration": request.total_duration,
        "created_at": request.created_at,
        "reviewed_at": request.reviewed_at,
        "admin_note": request.admin_note,
        "submitted_by_email": request.submitted_by.email if request.submitted_by else None
    }


@router.post("/annotation-requests/{request_id}/review")
async def review_annotation_request(
    request_id: int,
    review: AnnotationRequestReview,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Approve or reject an annotation request (admin only).

    If approved, annotations are automatically pushed to GitHub repository.
    """
    from ..github_integration import push_approved_annotation

    request = db.query(AnnotationRequest).filter(
        AnnotationRequest.id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Demande non trouvee")

    if request.status != AnnotationRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Cette demande a deja ete traitee")

    if review.action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action invalide (approve ou reject)")

    # Update status
    request.status = AnnotationRequestStatus.APPROVED if review.action == "approve" else AnnotationRequestStatus.REJECTED
    request.reviewed_at = datetime.now()
    request.reviewed_by_id = admin.id
    request.admin_note = review.note

    result_message = ""
    github_result = None

    # If approved, push to GitHub
    if review.action == "approve":
        try:
            annotations = json.loads(request.annotations_data)
            user_email = request.submitted_by.email if request.submitted_by else "unknown"

            # Push to GitHub
            github_result = await push_approved_annotation(
                audio_path=request.audio_path,
                annotations_data=annotations,
                model_type=request.model_type,
                user_email=user_email,
                request_id=request.id
            )

            if github_result["success"]:
                result_message = f"Approuve et pousse sur GitHub: {len(annotations)} annotations"
            else:
                # GitHub push failed but we still approve
                result_message = f"Approuve (GitHub: {github_result.get('error', 'erreur inconnue')})"

        except Exception as e:
            # On error, revert approval
            request.status = AnnotationRequestStatus.PENDING
            request.reviewed_at = None
            request.reviewed_by_id = None
            db.commit()
            raise HTTPException(status_code=500, detail=f"Erreur lors de l'approbation: {str(e)}")
    else:
        result_message = "Demande rejetee"

    db.commit()

    response = {
        "message": result_message,
        "request_id": request_id,
        "new_status": request.status,
        "reviewed_by": admin.email
    }

    if github_result:
        response["github"] = github_result

    return response


# ==============================================================================
# USER MANAGEMENT
# ==============================================================================

@router.post("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Grant admin rights to a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouve")

    user.is_admin = True
    db.commit()

    return {"message": f"Utilisateur {user.email} est maintenant administrateur"}


@router.get("/users")
async def get_all_users(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).order_by(User.created_at.desc()).all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
            "created_at": u.created_at
        }
        for u in users
    ]
