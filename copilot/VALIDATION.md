# Validation record — 2026-10-27

Status: **connector and live Resemble API checks passed; Microsoft Cowork host end-to-end test pending**.

## Completed

- 34 automated tests passed: authenticated MCP, tool schemas and safety annotations, direct uploads, malformed inputs, partial results, mixed audio/video evidence, zero-valued scores, question lifecycle, bounded uploads, upstream failures, and package gates.
- Microsoft `@microsoft/app-manifest` 1.1.3 accepted the manifest against Microsoft's v1.29 schema with zero errors. This is schema validation, not service validation or store approval.
- Production entrypoint started with both MCP surfaces. Legacy `/mcp` initialized successfully, health returned healthy, and `/cowork/mcp` returned the expected unauthenticated 401 challenge.
- Real MCP SDK client → local connector → production Resemble API completed the synthetic/non-sensitive jobs below. API-key credentials were used for these tests, not Microsoft OAuth. Every recorded tool call finished in under 2.2 seconds; inference was polled separately.

| Test | Result |
|---|---|
| PNG attachment | Completed |
| Synthetic speech WAV attachment | Completed |
| Public HTTPS image | Completed |
| MP4 attachment with synthetic speech | Completed; separate audio and video results |
| Generated text passage | Completed |
| Follow-up question on completed image | Completed; answer returned |
| Follow-up question on completed video | Completed; answer returned |

These demonstrate functional integration only, not detector accuracy or real-world effectiveness. The fixtures were a Resemble logo, system-generated speech, a logo video with that speech, and generated test prose. No customer media was used.

## Still required

- Save an owner-approved, dedicated Resemble OAuth registration; the prepared registration is currently unsaved.
- Sign into Microsoft 365, create the corresponding OAuth token-vault registration, and replace the manifest's registration placeholder.
- Deploy the new connector to a reachable HTTPS host before Microsoft calls it. The public production `/cowork/mcp` endpoint has not been deployed by this work.
- Run Microsoft service package validation and personal installation, then verify skill activation, OAuth consent/code exchange, attachment mapping, live tool results, refresh, and revocation in Cowork itself.
- Public store submission and Microsoft review are not performed.

The release builder refuses a missing or placeholder OAuth registration. The generated DRAFT ZIP is only for offline review and must not be represented as an installable, working plugin.

Raw local evidence is saved under ignored `copilot/evidence/`: `live-smoke.json`, `live-video.json`, `live-question.json`, `combined-server.json`, and `microsoft-schema-validation.json`. No credentials are recorded.
