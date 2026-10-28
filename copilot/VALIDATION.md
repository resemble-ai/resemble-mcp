# Validation record — 2026-10-27

Status: **the original authenticity workflows and 1.0.1 audio correction are verified in deployed Microsoft Cowork. Version 1.1.0 Signal passes local/live-API and package validation; its deployment and Cowork activation tests remain pending**.

## Completed

- 41 automated tests passed (36 original checks plus five unavailable-audio regression cases): authenticated MCP, tool schemas and safety annotations, direct uploads, malformed inputs, partial results, mixed audio/video evidence, zero-valued scores, question lifecycle, bounded uploads, upstream failures, and package gates.
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

## Deployed verification

PR #9 was merged by the repository owner and deployed to the existing Resemble MCP service. Production health advertises `/cowork/mcp`; unauthenticated access returns 401 and protected-resource metadata points to Resemble's authorization server. A real MCP client against the deployed endpoint completed image, video-with-audio, text, and follow-up-question jobs. The slowest recorded call was 1.298 seconds. These used API-key credentials and are still distinct from Microsoft-host OAuth testing.

## Microsoft Cowork host verification

The tenant administrator activated Cowork billing. A licensed work account opened Cowork, installed version 1.0.0, enabled all three skills, and connected through the dedicated Resemble OAuth client. The owner completed team-specific consent. Cowork visibly showed Connected and executed all six tools against the deployed endpoint.

| Host case | Observed result |
|---|---|
| Public Resemble logo URL | Completed; image label Real, score 0.030211485104490374 |
| Analyst follow-up | Question submitted once and polled to a completed answer |
| Generated text passage | Completed; prediction ai, confidence 0.9713 |
| Cowork-created PNG, 3,565 bytes | Completed; actual workspace-path mapping delivered the file; image score 0.2405310515040822 |
| Cowork-created WAV tone, 160,044 bytes | Completed; correct filename, audio type and 5-second duration; no usable audio scores |
| Cowork-created MP4, 44,846 bytes | Completed; correct filename, video type and 5-second duration; video score 0.04680093312396712, separate unavailable audio |

The host had ffmpeg but no usable offline speech synthesizer. WAV/MP4 host tests therefore used a 440 Hz tone, not spoken audio. Earlier API-backed tests used synthesized speech. Neither is an accuracy benchmark. One parallel media call was definitively blocked by Cowork's approval system before execution; its sequential retry succeeded. No uncertain submission was retried.

The actual job IDs and results were independently retrieved through Resemble's API. That read-only API-key verification supplements the Cowork tool trace; it does not replace the OAuth host test. Raw host traces, connection/result screenshots, and job IDs remain in ignored local evidence to avoid publishing account details.

Installed/tested 1.0.0 ZIP SHA-256: `05d52e334a14cbf4ec3103c5639d526858136fbdbcd554fbb5ab9595cf693b0e`.

## Edge case found and corrected in 1.0.1

The no-speech fixtures returned audio `label: real`, `score: [null]`, and `aggregated_score: -1.0`. Cowork correctly explained that these did not establish authenticity, but the connector should make that state explicit. Updated normalization marks audio without any finite nonnegative score as unavailable, preserves the upstream label under `reported_label`, and preserves raw scores and independent video results. Valid zeros remain valid.

All 41 automated tests pass. The updated local MCP connector also read the actual Cowork-created WAV/MP4 jobs from production Resemble and returned unavailable audio while retaining the video result. A previously completed speech-containing MP4 retained its usable audio assessment. No new jobs were submitted for that regression check. The owner subsequently merged PR #10. Production returned the corrected fields, and a fresh Cowork task reread the existing WAV/MP4 jobs through OAuth, confirming unavailable audio and preserved video results without new submissions. Evidence: `cowork-deployed-fix.txt`, `cowork-deployed-fix.png`, and `host-validation-final.json`.

The 1.0.1 package passed Microsoft service validation. ZIP SHA-256: `b6d3be423f0605e78619ae097336caa21a815e887cd05623170c69f98eb8b2c3`.

## Signal 1.1.0 validation

- 65 automated tests pass, including Signal input/schema validation, source attribution without URL fetching, exact-text forwarding, direct media delivery, output privacy, zero scores, unavailable responses, and non-retrying error/timeout behavior.
- The live Signal API accepted benign and synthetic wire-diversion text fixtures. The updated local MCP connector completed a public documentation excerpt, synthetic fraud text, and a PNG attachment against production Signal. Calls took 4.141–4.330 seconds. These used an API key and are not Microsoft-host OAuth tests.
- The documentation excerpt returned suspicious while the synthetic wire-diversion text returned fraud and the PNG returned safe. These are observed responses, not an accuracy benchmark. The skill explains that educational descriptions of fraud can match categories and that reference examples are not quotes from the source.
- Microsoft service validation passed for the release ZIP with the existing OAuth registration. No new scopes, client, or tenant permissions were requested. SHA-256: `6bb4c09419a92cac8b4591cf31f06f09d421532333da4e9196870a2e79a69832`.
- Signal evidence: `signal-api-preflight.json`, `signal-local-mcp-live.json`, and `microsoft-package-validation-1.1.0.txt` in the ignored local evidence directory.

Automatic selection is not yet tested. Microsoft explicitly documents context-based skill selection and unsupported plugin event hooks. Neither a successful direct Signal call nor a successful automatic-selection sample can establish universal web interception. The optional custom-instruction paragraph strengthens prompting but does not supply an enforcement boundary.

## Remaining release checks

- Deploy Signal and verify explicit tool execution plus ordinary web-query skill activation in Cowork. Package acceptance alone does not prove either.
- Access-token refresh after expiry and upstream grant revocation/reconnection are not yet verified in the host. Automated rejection tests do not replace those lifecycle checks.
- Speech-containing workspace attachments remain untested in Cowork; image, tone WAV, and mixed video/tone delivery are verified.
- Public store submission, cross-tenant installation, and Microsoft review are not performed. The OAuth registration remains restricted to the home tenant.

The release builder refuses a missing or placeholder OAuth registration. The separately generated DRAFT ZIP is for offline review only.

Local evidence under ignored `copilot/evidence/` includes API smoke records, Microsoft schema/service validation and installation records, OAuth setup screenshots, `cowork-image-question.txt`, `cowork-text.txt`, `cowork-file-mapping.txt`, `cowork-files.txt`, `cowork-jobs-api-verification.json`, and `unscored-audio-live-regression.json`. No access tokens, passwords, or client secrets are recorded.
