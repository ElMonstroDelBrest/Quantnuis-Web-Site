#!/bin/bash
# ==============================================================================
# Créer une distribution CloudFront devant le bucket S3 projet-quantnuis-frontend
# ==============================================================================
#
# Pourquoi : exposer le frontend en HTTPS (le S3 website endpoint est HTTP only)
# et bénéficier d'un CDN mondial avec cache.
#
# Coût :
#   - Gratuit jusqu'à 1 TB de transfert/mois + 10M requêtes/mois (free tier AWS
#     permanent, pas limité aux 12 premiers mois).
#   - Pour un salon : largement dans le free tier.
#
# Prérequis :
#   - AWS CLI configuré avec droits cloudfront:*
#   - Le bucket projet-quantnuis-frontend doit avoir le static-website hosting
#     activé et être public (déjà le cas selon CLAUDE.md).
#
# Résultat : domaine <distribution-id>.cloudfront.net utilisable en HTTPS.
# ==============================================================================

set -euo pipefail

REGION="${AWS_REGION:-eu-west-3}"
BUCKET="${S3_BUCKET:-projet-quantnuis-frontend}"
ORIGIN_DOMAIN="${BUCKET}.s3-website.${REGION}.amazonaws.com"
CALLER_REF="quantnuis-frontend-$(date +%s)"

echo "==> Vérification que le bucket ${BUCKET} a le website hosting activé..."
aws s3api get-bucket-website --bucket "${BUCKET}" > /dev/null \
  || { echo "❌ Le bucket n'a pas le static-website hosting. Activer d'abord avec :"; \
       echo "   aws s3 website s3://${BUCKET} --index-document index.html --error-document index.html"; \
       exit 1; }
echo "   OK."

echo "==> Recherche d'une distribution CloudFront existante pour ${ORIGIN_DOMAIN}..."
EXISTING=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName=='${ORIGIN_DOMAIN}']].Id | [0]" \
  --output text)

if [[ "${EXISTING}" != "None" && -n "${EXISTING}" ]]; then
  echo "   Distribution déjà existante : ${EXISTING}"
  DIST_ID="${EXISTING}"
else
  echo "==> Création de la distribution CloudFront..."
  CONFIG_FILE=$(mktemp)
  cat > "${CONFIG_FILE}" <<EOF
{
  "CallerReference": "${CALLER_REF}",
  "Comment": "Quantnuis frontend (HTTPS + CDN devant S3 website)",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "s3-website-origin",
        "DomainName": "${ORIGIN_DOMAIN}",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginSslProtocols": { "Quantity": 1, "Items": ["TLSv1.2"] },
          "OriginReadTimeout": 30,
          "OriginKeepaliveTimeout": 5
        },
        "CustomHeaders": { "Quantity": 0 }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "s3-website-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] }
    },
    "Compress": true,
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6"
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      { "ErrorCode": 403, "ResponsePagePath": "/index.html", "ResponseCode": "200", "ErrorCachingMinTTL": 0 },
      { "ErrorCode": 404, "ResponsePagePath": "/index.html", "ResponseCode": "200", "ErrorCachingMinTTL": 0 }
    ]
  },
  "PriceClass": "PriceClass_100",
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": true,
    "MinimumProtocolVersion": "TLSv1",
    "CertificateSource": "cloudfront"
  },
  "HttpVersion": "http2"
}
EOF

  DIST_ID=$(aws cloudfront create-distribution \
    --distribution-config "file://${CONFIG_FILE}" \
    --query "Distribution.Id" --output text)
  rm -f "${CONFIG_FILE}"
  echo "   Distribution créée : ${DIST_ID}"
fi

DIST_DOMAIN=$(aws cloudfront get-distribution --id "${DIST_ID}" \
  --query "Distribution.DomainName" --output text)

echo ""
echo "=============================================="
echo "✅ CloudFront en place"
echo "=============================================="
echo ""
echo "  Distribution ID  : ${DIST_ID}"
echo "  URL HTTPS        : https://${DIST_DOMAIN}"
echo ""
echo "⏳ Le déploiement CloudFront prend 5-15 minutes avant d'être pleinement actif."
echo ""
echo "Étapes suivantes :"
echo "  1. GitHub Actions → ajouter secret CLOUDFRONT_DISTRIBUTION_ID = ${DIST_ID}"
echo "  2. Dans .github/workflows/deploy-frontend.yml, décommenter le bloc"
echo "     'Invalidate CloudFront cache' (déjà préparé)"
echo "  3. Tester : curl -I https://${DIST_DOMAIN}"
echo "  4. (Optionnel) Attacher un domaine custom via Route53 + ACM cert en us-east-1"
