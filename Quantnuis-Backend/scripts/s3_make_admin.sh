#!/bin/bash
# ==============================================================================
# Script pour promouvoir un utilisateur en admin
# Telecharge la BDD depuis S3, modifie l'utilisateur, et re-upload
#
# Usage: ./scripts/s3_make_admin.sh spectro-test@test.com
# ==============================================================================

set -e

EMAIL="${1:-spectro-test@test.com}"
BUCKET="quantnuis-db-bucket"
DB_FILE="quantnuis.db"
TMP_DB="/tmp/quantnuis_admin_edit.db"

echo "=== Promotion de $EMAIL en admin ==="

# 1. Telecharger la BDD depuis S3
echo "[1/4] Telechargement de la BDD depuis S3..."
aws s3 cp "s3://$BUCKET/$DB_FILE" "$TMP_DB"

# 2. Verifier que l'utilisateur existe
echo "[2/4] Verification de l'utilisateur..."
USER_EXISTS=$(sqlite3 "$TMP_DB" "SELECT COUNT(*) FROM users WHERE email='$EMAIL';")
if [ "$USER_EXISTS" -eq 0 ]; then
    echo "Erreur: Utilisateur $EMAIL non trouve!"
    echo "Utilisateurs disponibles:"
    sqlite3 "$TMP_DB" "SELECT email, is_admin FROM users;"
    rm -f "$TMP_DB"
    exit 1
fi

# 3. Modifier l'utilisateur
echo "[3/4] Promotion en admin..."
sqlite3 "$TMP_DB" "UPDATE users SET is_admin = 1 WHERE email='$EMAIL';"

# Verifier
IS_ADMIN=$(sqlite3 "$TMP_DB" "SELECT is_admin FROM users WHERE email='$EMAIL';")
echo "    is_admin = $IS_ADMIN"

# 4. Re-uploader la BDD
echo "[4/4] Upload de la BDD vers S3..."
aws s3 cp "$TMP_DB" "s3://$BUCKET/$DB_FILE"

# Nettoyage
rm -f "$TMP_DB"

echo ""
echo "=== Succes! ==="
echo "$EMAIL est maintenant administrateur."
echo "Reconnectez-vous sur le site pour voir les changements."
