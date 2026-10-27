# Validation record — 2026-10-27

Status: **connector and live Resemble API checks passed; Microsoft Cowork host end-to-end test pending**.

## Completed

- 36 automated tests passed: authenticated MCP, tool schemas and safety annotations, direct uploads, malformed inputs, partial results, mixed audio/video evidence, zero-valued scores, question lifecycle, bounded uploads, upstream failures, and package gates.
- Microsoft `@microsoft/app-manifest` 1.1.3 accepted the manifest against Microsoft's v1.29 schema with zero errors. This is schema validation, not service validation or store approval.
- Microsoft service package validation through Agents Toolkit passed all 59 rules for the actual 1.0.0 ZIP containing the registered OAuth reference. The first validation caught Microsoft's nonzero-major-version requirement; corrected before installation.
- Saved the owner-approved dedicated Resemble public OAuth client and registered it with Microsoft's token vault through `oauth/register`, using PKCE, no shared secret, and the home tenant restriction. Verified the resulting settings in Developer Portal. Its form currently requires a secret even with PKCE, so the checked-in toolkit configuration is the reproducible registration path.
- Personal package installation through `atk install` succeeded after Microsoft's RAI validation. Install identifiers are saved in local evidence. This establishes package acceptance, not successful Cowork tool execution.
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

- Deploy the new connector to a reachable HTTPS host before Microsoft calls it. The public production `/cowork/mcp` endpoint has not been deployed by this work.
- Enable Cowork usage-based billing for the test account. The tenant Cowork admin page currently reports that billing is not configured; no billing changes were made.
- Complete host testing with a licensed Copilot account. The administrator account used for registration and personal installation has only Teams Exploratory; Cowork is absent from its UI. A separate licensed work account is needed.
- Verify skill activation, OAuth consent/code exchange, attachment mapping, live tool results, refresh, and revocation in Cowork itself.
- Public store submission and Microsoft review are not performed.

The release builder refuses a missing or placeholder OAuth registration. The tenant-scoped 1.0.0 ZIP has been installed for testing, but is not yet a verified working plugin. The separately generated DRAFT ZIP remains for offline review only.

Raw local evidence is saved under ignored `copilot/evidence/`: `live-smoke.json`, `live-video.json`, `live-question.json`, `combined-server.json`, `microsoft-schema-validation.json`, `microsoft-package-validation.txt`, and `microsoft-install.json`, plus registration screenshots. No access tokens, passwords, or client secrets are recorded.
