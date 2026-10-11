# Changelog

All notable changes to RepoGPT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-11
### Added
- Monorepo layout and development tooling.
- Core settings configuration with Pydantic Settings and strict validation.
- Standardized error handling envelope and custom `AppError` hierarchy.
- Structured logging with `structlog` and automatic secret scrubbing.
- Cryptographic primitives: Argon2id password hashing, JWT access tokens, Fernet secret encryption.
- PyMongo native async integration with idempotent MongoDB index creation.
- Redis client connection pool and sliding-window rate limiting.
- Healthcheck endpoints `/live` and `/ready`.
- Docker Compose configurations for base, dev, and production.
- Production Caddy reverse proxy setup with strict Content Security Policy.
- React 19 + Vite frontend shell with Tailwind CSS v4, dark theme tokens, landing page, and dashboard.
- GitHub Actions CI/CD workflows for testing, security audits, and EC2 deployment.
