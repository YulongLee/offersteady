## 1. Shared project baseline

- [x] 1.1 Establish the unified repo-level directory conventions for apps, packages, infra, docs, ai and tests
- [x] 1.2 Add shared environment-variable and typed configuration foundations for frontend and backend
- [x] 1.3 Add shared logging field conventions and common runtime metadata helpers

## 2. Backend platform foundation

- [x] 2.1 Refactor `apps/backend` into a production-grade module layout covering API routers, schemas, services, repositories/adapters, config and middleware
- [x] 2.2 Introduce unified API response envelopes, versioning rules and reusable error models
- [x] 2.3 Introduce centralized exception handling, request-id propagation and structured backend logging hooks
- [x] 2.4 Add production-oriented configuration loading for FastAPI, including app mode, database, pgvector and OSS settings

## 3. Data and storage integration baseline

- [x] 3.1 Add PostgreSQL connection scaffolding, health checks and dependency boundaries without implementing business repositories
- [x] 3.2 Add pgvector extension initialization and retrieval-boundary scaffolding without implementing RAG logic
- [x] 3.3 Add Aliyun OSS storage configuration and adapter boundaries as the canonical object-storage foundation
- [x] 3.4 Add migration/tooling placeholders and conventions for future schema evolution

## 4. Frontend and deployment baseline

- [x] 4.1 Align the React + TypeScript app with the shared configuration and API-platform conventions without changing product interactions
- [x] 4.2 Add Docker build/runtime assets for web, backend and supporting services
- [x] 4.3 Add Nginx baseline configuration for static asset serving and API reverse proxying
- [x] 4.4 Add one production-like multi-service startup baseline for local and deployment-oriented environments

## 5. Documentation and verification

- [x] 5.1 Update architecture and engineering docs to describe the production-grade foundation, module rules and deployment baseline
- [x] 5.2 Document the canonical environment variables, secret boundaries and local setup assumptions
- [x] 5.3 Add verification coverage for unified response structure, configuration loading and infrastructure health boundaries
- [x] 5.4 Run `openspec validate establish-production-grade-foundation --strict`
