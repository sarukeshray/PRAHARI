# PRAHARI backend.
#
# Uses requirements-deploy.txt, which omits PyTorch. See that file for what
# changes as a result and how it was measured.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a code change does not reinstall them.
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

COPY . .

# Uploaded photographs and the SQLite file live here. On a platform without a
# persistent volume this is wiped on redeploy, and boot.py reseeds.
RUN mkdir -p data/uploads

ENV ENV=production \
    DB_BACKEND=sqlite \
    PORT=8000

EXPOSE 8000

# Seed and score on first boot, then serve. Both steps are skipped if the
# database already has content.
CMD ["sh", "-c", "python boot.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
