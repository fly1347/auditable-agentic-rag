# Security Baseline

## 1. Security Goals

The public release provides a verifiable engineering security baseline:

- identity can only come from a trusted access layer;
- unregistered sources are denied by default;
- invisible evidence cannot enter TopK, the prompt, or citations;
- identity permission, data category, and provider are checked before data egress;
- queries, logs, and release materials pass safety and redaction checks;
- security decisions are recorded in CER for audit and replay.

These capabilities support a local reference implementation and contract validation. They do not replace enterprise IAM, DLP, SIEM, or compliance auditing.

## 2. Trusted Identity

The API uses a static-token adapter to map tokens to `Principal` objects. Roles, groups, tenant, and the `public_egress` capability come from server-side configuration and cannot be declared by request JSON.

The public sample defines four identity semantics:

| Identity | Typical permissions |
| :-- | :-- |
| public | Read public sources; may receive public-cloud egress capability when configured |
| engineer | Read public and platform-engineering material |
| analyst | Read public and analysis material |
| admin | Administration and diagnostics; egress still requires explicit policy authorization |

Static tokens are appropriate for localhost demos. Before exposing the service externally, replace all example tokens and use a reverse proxy, TLS, and a proper identity system.

## 3. Source ACL

`policy/source_acl.yaml` is the source-level authorization registry and uses `default_behavior: deny`.

Public sample sources:

| source_id | visibility | Allowed roles/groups |
| :-- | :-- | :-- |
| `public_rag.md` | public | All identities |
| `internal_platform.md` | internal_demo | engineer/admin, platform/admin |
| `analyst_note.md` | internal_demo | analyst/admin, product/admin |

The loader derives stable `source_id` values from relative paths and injects ACL metadata from the Registry before indexing. If a new document is unregistered, its `source_id` does not match, or ACL fields are invalid, index construction fails.

The retriever filters ACL and tenant eligibility before TopK. Invisible chunks therefore cannot participate in final ranking, evidence selection, the prompt, or citations.

## 4. Data Egress Control

Every provider attempt performs an independent egress check based primarily on:

- whether the Principal has the required egress capability;
- evidence visibility and data category;
- whether the provider is allowed by configuration;
- public / restricted cloud policy;
- runtime budget and call-count limits.

The public configuration allows public evidence to be sent to configured public-cloud providers. Restricted evidence is denied by default. `fallback_chain: []`, so the runtime does not silently switch to another model path after failure.

## 5. Query Safety and Prompt Injection

Query safety runs before retrieval and model calls and can reject clearly dangerous input directly. The prompt template instructs the model to treat retrieved document content as untrusted evidence and not execute instructions embedded in documents.

`sample_data/security_cases/malicious_prompt_injection_demo.md.disabled` is disabled by default and excluded from the corpus index. It documents the boundary for indirect document-level injection.

Current Query Safety, Prompt Injection checks, and redaction primarily rely on rules and fixed negative controls. They do not cover all language variants, encoding bypasses, indirect injections, or tool attacks.

## 6. CER, Logs, and Redaction

CER records the Principal projection, policy decisions, egress decisions, retrieval/evidence/prompt lineage, model calls, timing, usage, outcome, and errors.

The public release excludes:

- raw CER and complete prompt-visible evidence;
- provider secrets, real `.env` files, and backups;
- raw query/audit/service logs;
- the complete private corpus, vectors, and model caches;
- experiments, process drafts, and historical Git workspaces.

The release scanner checks secret patterns, private paths, backup files, raw logs, and out-of-scope artifacts. Manual review is still required for newly added fields, answers, error messages, and documentation links.

## 7. Security Validation

Offline security entry point:

```bash
PYTHONPATH=src:. python eval/run_security_smoke.py \
  --output-dir artifacts/security-smoke
```

The public repository also retains four core governance and audit contract test files (currently 11 tests) covering source-registry, provider-egress, audit-projection, and CER invariants. The complete release gate includes:

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -q
python scripts/release_scan.py .
```

The current offline security smoke contains 16 assertions covering identity, authentication, admin defaults, query safety, prompt injection, tenant ACL, egress, redaction, and public CER sanitization directly.

These commands do not automatically authorize provider calls. Online evaluation must explicitly permit model calls and the corresponding data-egress policy.

## 8. Current Boundary

- Static tokens are not OIDC/OAuth2 or an enterprise IdP.
- Tenant isolation is mainly validated through synthetic negative controls.
- JSONL audit storage is intended for single-process local execution.
- Key rotation, revocation administration, centralized audit, DLP, and SIEM are not integrated.
- Security capabilities are an engineering baseline, not a production compliance claim.
