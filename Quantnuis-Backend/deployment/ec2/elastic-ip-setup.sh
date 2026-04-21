#!/bin/bash
# ==============================================================================
# Attacher une Elastic IP à l'instance EC2 quantnuis-api-ec2
# ==============================================================================
#
# Pourquoi : sans Elastic IP, l'IP publique de l'EC2 change à chaque reboot,
# ce qui casse `environment.prod.ts`, le cert HTTPS (nip.io) et les DNS clients.
#
# Coût : ~3,60 €/mois tant que l'Elastic IP est allouée mais NON attachée à une
# instance running. Gratuit tant qu'elle est attachée à une instance running.
#
# Prérequis : AWS CLI configuré avec profil ayant les droits ec2:*
#
# Ce script est IDEMPOTENT : ré-exécuter ne crée pas de doublon.
# ==============================================================================

set -euo pipefail

REGION="${AWS_REGION:-eu-west-3}"
INSTANCE_NAME="${INSTANCE_NAME:-quantnuis-api-ec2}"
EIP_TAG_NAME="${EIP_TAG_NAME:-quantnuis-api-eip}"

echo "==> Recherche de l'instance EC2 nommée '${INSTANCE_NAME}' dans ${REGION}..."
INSTANCE_ID=$(aws ec2 describe-instances \
  --region "${REGION}" \
  --filters "Name=tag:Name,Values=${INSTANCE_NAME}" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text)

if [[ "${INSTANCE_ID}" == "None" || -z "${INSTANCE_ID}" ]]; then
  echo "❌ Aucune instance running trouvée avec le tag Name=${INSTANCE_NAME}"
  exit 1
fi
echo "   Instance trouvée : ${INSTANCE_ID}"

echo "==> Recherche d'une Elastic IP existante nommée '${EIP_TAG_NAME}'..."
EXISTING_ALLOC=$(aws ec2 describe-addresses \
  --region "${REGION}" \
  --filters "Name=tag:Name,Values=${EIP_TAG_NAME}" \
  --query "Addresses[0].AllocationId" \
  --output text)

if [[ "${EXISTING_ALLOC}" != "None" && -n "${EXISTING_ALLOC}" ]]; then
  ALLOCATION_ID="${EXISTING_ALLOC}"
  EIP=$(aws ec2 describe-addresses --region "${REGION}" --allocation-ids "${ALLOCATION_ID}" --query "Addresses[0].PublicIp" --output text)
  echo "   Elastic IP déjà existante : ${EIP} (${ALLOCATION_ID})"
else
  echo "==> Allocation d'une nouvelle Elastic IP..."
  ALLOCATION_ID=$(aws ec2 allocate-address \
    --region "${REGION}" \
    --domain vpc \
    --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=${EIP_TAG_NAME}}]" \
    --query "AllocationId" --output text)
  EIP=$(aws ec2 describe-addresses --region "${REGION}" --allocation-ids "${ALLOCATION_ID}" --query "Addresses[0].PublicIp" --output text)
  echo "   Elastic IP allouée : ${EIP} (${ALLOCATION_ID})"
fi

echo "==> Association de l'Elastic IP à l'instance..."
aws ec2 associate-address \
  --region "${REGION}" \
  --instance-id "${INSTANCE_ID}" \
  --allocation-id "${ALLOCATION_ID}" \
  --allow-reassociation \
  > /dev/null
echo "   Associée."

echo ""
echo "=============================================="
echo "✅ Elastic IP configurée : ${EIP}"
echo "=============================================="
echo ""
echo "Étapes suivantes (manuelles) :"
echo "  1. Mettre à jour Quantnuis-Frontend/src/environments/environment.prod.ts :"
echo "       apiUrl: 'https://${EIP//./-}.nip.io'"
echo "  2. Sur l'EC2, re-émettre le certificat Certbot pour le nouveau hostname nip.io :"
echo "       sudo certbot --nginx -d ${EIP//./-}.nip.io"
echo "  3. Rebuild + redéployer le frontend (CI/CD ou workflow GitHub Actions)."
echo "  4. Vérifier : curl -I https://${EIP//./-}.nip.io/health"
