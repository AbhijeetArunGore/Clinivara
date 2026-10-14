# Clinivara Production Deployment Guide

## 1. Local Development vs. Production Settings

| Parameter | Local Development Default | Production Recommended |
| :--- | :--- | :--- |
| `CLINIVARA_APP_ENV` | `development` | `production` |
| `CLINIVARA_DEBUG` | `true` | `false` |
| `CLINIVARA_AUTH_SECRET_KEY` | Hardcoded development key | Injected via AWS Secrets Manager, Vault, or GCP Secret Manager ($\ge 32$ chars) |
| `CLINIVARA_STORAGE_ROOT` | `data/storage` | High-security mounted volume with encryption-at-rest (POSIX 0700 permissions) |
| `CLINIVARA_OCR_ENABLED` | `true` | `true` (Tesseract system binaries pre-baked in container) |
| Container User | Non-root `clinivara:1001` | Non-root `clinivara:1001` (enforced in Dockerfile) |

---

## 2. Docker Deployment

### Build and Run with Docker Compose
```bash
docker compose up -d --build
```

### Inspect Container Logs
```bash
docker compose logs -f clinivara-backend
```

### Run Container Healthcheck
```bash
curl -f http://localhost:8000/api/v1/health
```

---

## 3. Operational Requirements & Hardening

1. **TLS / HTTPS**: All external traffic must terminate on an edge reverse proxy (NGINX, Traefik, AWS ALB) enforcing TLS 1.3.
2. **Read-Only Root Filesystem**: The container root filesystem should be mounted read-only, allowing writes only to designated volume paths (`/app/data/storage` and `/app/data/audit`).
3. **Key Management**: Secrets must never be stored in Git or container images. Use Kubernetes Secrets or cloud secret managers.
4. **Malware Scanning Integration**: For high-risk deployments, integrate an upstream antivirus/sandbox scanner (such as ClamAV or sandbox service) before files reach Boundary A staging.
5. **Data Retention & Shredding**: Implement automated lifecycle policies on Boundary A original files to shred records after the statutory retention period.
