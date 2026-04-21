#!/usr/bin/env bash
# ==============================================================================
# QUANTNUIS LAMBDA — SCRIPT DE DÉPLOIEMENT
# ==============================================================================
# Usage:
#   cd Quantnuis-Backend
#   bash deploy_lambda.sh
# ==============================================================================

set -e

REGION="eu-west-3"
BUCKET="quantnuis-db-bucket"
S3_KEY="codebuild/source.zip"
CODEBUILD_PROJECT="quantnuis-lambda-deploy"
LAMBDA_FUNCTION="quantnuis-api"

echo "=============================================="
echo "  Quantnuis Lambda — Déploiement"
echo "=============================================="

# 1. Créer le zip du code source (sans venv, data, __pycache__)
echo ""
echo "[1/3] Création du zip source..."
python3 - <<'PYEOF'
import zipfile, os
from pathlib import Path

root = Path(__file__).parent if "__file__" in dir() else Path(".")
# Chercher la racine Quantnuis-Backend
if not (root / "Dockerfile.lambda").exists():
    root = Path(".")

skip_dirs = {"venv", "__pycache__", ".git", "data", "notebooks",
             "benchmark_results", ".pytest_cache"}
skip_ext  = {".pyc", ".pyo"}
skip_files = {".env"}

out = "/tmp/quantnuis-lambda-src.zip"
count = 0

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in root.rglob("*"):
        parts = set(f.relative_to(root).parts)
        if parts & skip_dirs:
            continue
        if f.suffix in skip_ext:
            continue
        if f.name in skip_files:
            continue
        if f.is_file():
            arcname = "Quantnuis-Backend/" + str(f.relative_to(root))
            zf.write(f, arcname)
            count += 1

size = os.path.getsize(out)
print(f"  {count} fichiers → {out} ({size/1e6:.1f} MB)")
PYEOF

# 2. Upload sur S3
echo ""
echo "[2/3] Upload sur S3..."
aws s3 cp /tmp/quantnuis-lambda-src.zip "s3://${BUCKET}/${S3_KEY}" \
    --region "$REGION" \
    --no-progress
echo "  OK → s3://${BUCKET}/${S3_KEY}"

# 3. Lancer CodeBuild
echo ""
echo "[3/3] Lancement du build CodeBuild..."
BUILD_ID=$(aws codebuild start-build \
    --region "$REGION" \
    --project-name "$CODEBUILD_PROJECT" \
    --query "build.id" --output text)
echo "  Build ID: $BUILD_ID"

# Attendre la fin du build
echo ""
echo "  En attente du build (peut prendre ~5 min)..."
while true; do
    STATUS=$(aws codebuild batch-get-builds \
        --region "$REGION" \
        --ids "$BUILD_ID" \
        --query "builds[0].[buildStatus,currentPhase]" \
        --output text 2>/dev/null)
    BUILD_STATUS=$(echo "$STATUS" | awk '{print $1}')
    PHASE=$(echo "$STATUS" | awk '{print $2}')
    printf "\r  Statut: %-12s  Phase: %-15s" "$BUILD_STATUS" "$PHASE"

    if [[ "$BUILD_STATUS" == "SUCCEEDED" ]]; then
        echo ""
        break
    elif [[ "$BUILD_STATUS" == "FAILED" || "$BUILD_STATUS" == "FAULT" || "$BUILD_STATUS" == "STOPPED" ]]; then
        echo ""
        echo ""
        echo "  ✗ Build échoué ! Vérifiez les logs CloudWatch :"
        echo "  https://eu-west-3.console.aws.amazon.com/cloudwatch/home?region=eu-west-3#logsV2:log-groups/log-group/\$252Faws\$252Fcodebuild\$252F${CODEBUILD_PROJECT}"
        exit 1
    fi
    sleep 10
done

# Vérification finale
echo ""
echo "=============================================="
echo "  Vérification Lambda..."
LAMBDA_STATE=$(aws lambda get-function \
    --function-name "$LAMBDA_FUNCTION" \
    --region "$REGION" \
    --query "Configuration.[State,LastModified]" \
    --output text 2>/dev/null)
echo "  State: $LAMBDA_STATE"

IMAGE_URI=$(aws lambda get-function \
    --function-name "$LAMBDA_FUNCTION" \
    --region "$REGION" \
    --query "Code.ImageUri" \
    --output text 2>/dev/null)
echo "  Image: $IMAGE_URI"

echo ""
echo "  ✓ Déploiement terminé !"
echo "=============================================="
