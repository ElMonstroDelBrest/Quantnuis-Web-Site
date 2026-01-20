# ==============================================================================
# DOCKERFILE - AWS LAMBDA COMPATIBLE
# ==============================================================================
# Image de base : AWS Lambda Python 3.11
# ==============================================================================

FROM public.ecr.aws/lambda/python:3.11

# Variables d'environnement pour les caches
ENV NUMBA_CACHE_DIR=/tmp
ENV MPLCONFIGDIR=/tmp
ENV TRANSFORMERS_CACHE=/tmp
ENV XDG_CACHE_HOME=/tmp

# Installer les outils de build nécessaires pour les packages Python
RUN yum install -y gcc gcc-c++ libsndfile && yum clean all

# Copier les requirements et installer les dépendances
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copier le code source
COPY config/ ${LAMBDA_TASK_ROOT}/config/
COPY shared/ ${LAMBDA_TASK_ROOT}/shared/
COPY models/ ${LAMBDA_TASK_ROOT}/models/
COPY database/ ${LAMBDA_TASK_ROOT}/database/
COPY pipeline/ ${LAMBDA_TASK_ROOT}/pipeline/
COPY api/ ${LAMBDA_TASK_ROOT}/api/

# Définir le handler
CMD ["api.main.handler"]
