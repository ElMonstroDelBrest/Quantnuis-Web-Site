#!/usr/bin/env python3
"""
================================================================================
                    SQLITE TO POSTGRESQL MIGRATION
================================================================================

Migrates data from SQLite database to PostgreSQL.

Usage:
    python -m scripts.migrate_sqlite_to_postgres \
        --sqlite-path data/quantnuis.db \
        --postgres-url postgresql://user:pass@localhost:5432/quantnuis

Options:
    --sqlite-path     Path to SQLite database file
    --postgres-url    PostgreSQL connection URL
    --dry-run         Show what would be migrated without making changes
    --skip-users      Skip user migration (if you want to recreate users)

================================================================================
"""

import argparse
import sys
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def create_sessions(sqlite_path: str, postgres_url: str):
    """Create database sessions for both SQLite and PostgreSQL."""
    # SQLite engine
    sqlite_engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False}
    )
    SqliteSession = sessionmaker(bind=sqlite_engine)

    # PostgreSQL engine
    postgres_engine = create_engine(postgres_url)
    PostgresSession = sessionmaker(bind=postgres_engine)

    return SqliteSession(), PostgresSession(), postgres_engine


def count_records(session, table_name: str) -> int:
    """Count records in a table."""
    result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    return result.scalar()


def migrate_users(sqlite_session, postgres_session, dry_run: bool = False):
    """Migrate users table."""
    print("\n[Users]")

    # Get users from SQLite
    result = sqlite_session.execute(text("""
        SELECT id, email, hashed_password, is_active, is_admin, created_at
        FROM users
    """))
    users = result.fetchall()

    print(f"  Found {len(users)} users in SQLite")

    if dry_run:
        for user in users[:5]:  # Show first 5
            print(f"    - {user.email} (admin={user.is_admin})")
        if len(users) > 5:
            print(f"    ... and {len(users) - 5} more")
        return len(users)

    # Insert into PostgreSQL
    migrated = 0
    for user in users:
        try:
            postgres_session.execute(text("""
                INSERT INTO users (id, email, hashed_password, is_active, is_admin, created_at)
                VALUES (:id, :email, :hashed_password, :is_active, :is_admin, :created_at)
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    hashed_password = EXCLUDED.hashed_password,
                    is_active = EXCLUDED.is_active,
                    is_admin = EXCLUDED.is_admin
            """), {
                "id": user.id,
                "email": user.email,
                "hashed_password": user.hashed_password,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "created_at": user.created_at
            })
            migrated += 1
        except Exception as e:
            print(f"    Error migrating user {user.email}: {e}")

    postgres_session.commit()
    print(f"  Migrated {migrated}/{len(users)} users")

    # Update sequence
    postgres_session.execute(text("""
        SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))
    """))
    postgres_session.commit()

    return migrated


def migrate_car_detections(sqlite_session, postgres_session, dry_run: bool = False):
    """Migrate car_detections table."""
    print("\n[Car Detections]")

    result = sqlite_session.execute(text("""
        SELECT id, filename, car_detected, confidence, probability,
               timestamp, status, audio_duration, user_id
        FROM car_detections
    """))
    detections = result.fetchall()

    print(f"  Found {len(detections)} car detections in SQLite")

    if dry_run:
        return len(detections)

    migrated = 0
    for det in detections:
        try:
            postgres_session.execute(text("""
                INSERT INTO car_detections
                    (id, filename, car_detected, confidence, probability,
                     timestamp, status, audio_duration, user_id)
                VALUES
                    (:id, :filename, :car_detected, :confidence, :probability,
                     :timestamp, :status, :audio_duration, :user_id)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": det.id,
                "filename": det.filename,
                "car_detected": det.car_detected,
                "confidence": det.confidence,
                "probability": det.probability,
                "timestamp": det.timestamp,
                "status": det.status,
                "audio_duration": det.audio_duration,
                "user_id": det.user_id
            })
            migrated += 1
        except Exception as e:
            print(f"    Error: {e}")

    postgres_session.commit()
    print(f"  Migrated {migrated}/{len(detections)} car detections")

    # Update sequence
    postgres_session.execute(text("""
        SELECT setval('car_detections_id_seq', (SELECT COALESCE(MAX(id), 1) FROM car_detections))
    """))
    postgres_session.commit()

    return migrated


def migrate_noisy_analyses(sqlite_session, postgres_session, dry_run: bool = False):
    """Migrate noisy_car_analyses table."""
    print("\n[Noisy Car Analyses]")

    result = sqlite_session.execute(text("""
        SELECT id, is_noisy, confidence, probability, estimated_db,
               timestamp, car_detection_id, user_id
        FROM noisy_car_analyses
    """))
    analyses = result.fetchall()

    print(f"  Found {len(analyses)} noisy car analyses in SQLite")

    if dry_run:
        return len(analyses)

    migrated = 0
    for analysis in analyses:
        try:
            postgres_session.execute(text("""
                INSERT INTO noisy_car_analyses
                    (id, is_noisy, confidence, probability, estimated_db,
                     timestamp, car_detection_id, user_id)
                VALUES
                    (:id, :is_noisy, :confidence, :probability, :estimated_db,
                     :timestamp, :car_detection_id, :user_id)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": analysis.id,
                "is_noisy": analysis.is_noisy,
                "confidence": analysis.confidence,
                "probability": analysis.probability,
                "estimated_db": analysis.estimated_db,
                "timestamp": analysis.timestamp,
                "car_detection_id": analysis.car_detection_id,
                "user_id": analysis.user_id
            })
            migrated += 1
        except Exception as e:
            print(f"    Error: {e}")

    postgres_session.commit()
    print(f"  Migrated {migrated}/{len(analyses)} noisy analyses")

    # Update sequence
    postgres_session.execute(text("""
        SELECT setval('noisy_car_analyses_id_seq', (SELECT COALESCE(MAX(id), 1) FROM noisy_car_analyses))
    """))
    postgres_session.commit()

    return migrated


def migrate_annotation_requests(sqlite_session, postgres_session, dry_run: bool = False):
    """Migrate annotation_requests table."""
    print("\n[Annotation Requests]")

    result = sqlite_session.execute(text("""
        SELECT id, filename, audio_path, annotations_data, model_type,
               status, annotation_count, total_duration, created_at,
               reviewed_at, admin_note, user_id, reviewed_by_id
        FROM annotation_requests
    """))
    requests = result.fetchall()

    print(f"  Found {len(requests)} annotation requests in SQLite")

    if dry_run:
        return len(requests)

    migrated = 0
    for req in requests:
        try:
            postgres_session.execute(text("""
                INSERT INTO annotation_requests
                    (id, filename, audio_path, annotations_data, model_type,
                     status, annotation_count, total_duration, created_at,
                     reviewed_at, admin_note, user_id, reviewed_by_id)
                VALUES
                    (:id, :filename, :audio_path, :annotations_data, :model_type,
                     :status, :annotation_count, :total_duration, :created_at,
                     :reviewed_at, :admin_note, :user_id, :reviewed_by_id)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": req.id,
                "filename": req.filename,
                "audio_path": req.audio_path,
                "annotations_data": req.annotations_data,
                "model_type": req.model_type,
                "status": req.status,
                "annotation_count": req.annotation_count,
                "total_duration": req.total_duration,
                "created_at": req.created_at,
                "reviewed_at": req.reviewed_at,
                "admin_note": req.admin_note,
                "user_id": req.user_id,
                "reviewed_by_id": req.reviewed_by_id
            })
            migrated += 1
        except Exception as e:
            print(f"    Error: {e}")

    postgres_session.commit()
    print(f"  Migrated {migrated}/{len(requests)} annotation requests")

    # Update sequence
    postgres_session.execute(text("""
        SELECT setval('annotation_requests_id_seq', (SELECT COALESCE(MAX(id), 1) FROM annotation_requests))
    """))
    postgres_session.commit()

    return migrated


def create_postgres_tables(postgres_engine):
    """Create tables in PostgreSQL using the ORM models."""
    print("\n[Creating PostgreSQL tables]")

    # Import models to register them with Base
    from database.models import User, CarDetection, NoisyCarAnalysis, AnnotationRequest
    from database.connection import Base

    Base.metadata.create_all(bind=postgres_engine)
    print("  Tables created successfully")


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL")
    parser.add_argument("--sqlite-path", required=True, help="Path to SQLite database")
    parser.add_argument("--postgres-url", required=True, help="PostgreSQL connection URL")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated")
    parser.add_argument("--skip-users", action="store_true", help="Skip user migration")

    args = parser.parse_args()

    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    print(f"SQLite: {args.sqlite_path}")
    print(f"PostgreSQL: {args.postgres_url.split('@')[1] if '@' in args.postgres_url else args.postgres_url}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)

    # Create sessions
    sqlite_session, postgres_session, postgres_engine = create_sessions(
        args.sqlite_path, args.postgres_url
    )

    # Create tables in PostgreSQL
    if not args.dry_run:
        create_postgres_tables(postgres_engine)

    # Migrate tables
    stats = {}

    if not args.skip_users:
        stats["users"] = migrate_users(sqlite_session, postgres_session, args.dry_run)

    stats["car_detections"] = migrate_car_detections(sqlite_session, postgres_session, args.dry_run)
    stats["noisy_analyses"] = migrate_noisy_analyses(sqlite_session, postgres_session, args.dry_run)
    stats["annotation_requests"] = migrate_annotation_requests(sqlite_session, postgres_session, args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    for table, count in stats.items():
        status = "would migrate" if args.dry_run else "migrated"
        print(f"  {table}: {count} records {status}")

    if args.dry_run:
        print("\nThis was a dry run. No changes were made.")
        print("Run without --dry-run to perform the actual migration.")

    # Cleanup
    sqlite_session.close()
    postgres_session.close()

    print("\nMigration complete!")


if __name__ == "__main__":
    main()
