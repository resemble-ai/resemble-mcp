# Resemble AI for Microsoft Copilot Cowork

Resemble-branded Microsoft 365 plugin source, with three skills and six live-service tools. This is a development candidate, **not a Microsoft-certified or published store listing**. A package passing schema validation is not evidence of a successful Cowork installation or OAuth connection.

The plugin checks audio, images, video, and text, and answers questions about completed detection reports. It sends only the inputs selected for a tool call to Resemble. Creation calls can consume credits. It does not send email, change files in Microsoft 365, or create a public media upload.

## What is included

| Component | Purpose |
|---|---|
| `appPackage/manifest.json` | M365 v1.29 manifest with `OAuthPluginVault` connector |
| `appPackage/skills/` | Media authenticity, text authenticity, detection brief |
| `appPackage/color.png`, `outline.png` | Required sizes, derived from the official logo in this repository |
| `../cowork_server.py` | Authenticated Streamable HTTP surface at `/cowork/mcp` |
| `build.py` | Deterministic ZIP, schema/skill/icon validation, missing-registration gate |
| `smoke.py` | MCP SDK test through the running connector to real Resemble APIs |
| `../tests/` | Protocol, errors, upload, auth, result semantics, and packaging tests |

Supported tools are `submit_media_detection`, `get_media_detection`, `submit_text_detection`, `get_text_detection`, `submit_detection_question`, and `get_detection_answer`. Media submissions accept a public HTTPS URL or a file up to 10 MiB. The file schema uses a top-level string with `contentEncoding: base64`, allowing Cowork to supply bytes outside the model context. This mapping must still be tested in the Cowork host.

Submitting and retrieving are separate operations. The server does not keep the client waiting for inference or automatically retry a POST. It shares a 20-second upstream budget across calls in a tool execution; account validation has a separate four-second budget. A submission timeout has an unknown outcome and must not trigger automatic resubmission. Exact scores, including zero, and distinct audio/video outcomes are preserved. Incomplete results do not expose partial verdict fields.

## Local development

From the repository root:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
.venv/bin/python copilot/build.py --draft
.venv/bin/uvicorn cowork_server:create_app --factory --host 127.0.0.1 --port 8879 --no-access-log
```

The normal `python server.py --sse` entrypoint mounts the same connector alongside `/mcp` and `/sse`. The Dockerfile includes it. Production endpoint availability is a separate deployment step.

Set `RESEMBLE_API_KEY` in the environment for a live **API-key smoke test**, or `RESEMBLE_ACCESS_TOKEN` for a live **OAuth-token smoke test**. Never put either into the manifest, a skill, a command argument, a checked-in file, or a screenshot.

```sh
.venv/bin/python copilot/smoke.py \
  --file copilot/appPackage/color.png \
  --url https://mcp.resemble.ai/static/logo-square-green.png \
  --text --question
```

Use purpose-made synthetic/non-sensitive audio and video fixtures for `--file`. These tests consume the selected Resemble account's credits. The script records job IDs, terminal states, limited detector fields, and timing under ignored `evidence/`. It saves submitted job IDs immediately so an interrupted test does not lose them. `--detect-uuid` resumes a media job without resubmitting it. Test outputs explicitly record `cowork_host_test: false`; a local MCP test is not the Microsoft-host test.

## OAuth setup required before installation

Cowork does not currently accept API-key authentication for this MCP connector. Never replace OAuth with anonymous access or embed a shared API key. Resemble's existing authorization server does not advertise dynamic client registration, so this package uses static OAuth registration.

Create a dedicated Resemble OAuth application for this integration, without altering existing clients:

| Setting | Value |
|---|---|
| Name | Resemble AI for Microsoft Copilot |
| Publisher | Resemble AI |
| Callback | `https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect` |
| Scopes | `openid api offline_access` |
| Client type | Public, PKCE S256; no shared client secret |
| Enabled | Yes, after owner approval |
| Listed / verified | Leave off until the applicable release review |

The current Resemble `api` scope is broad customer API access, subject to team permissions; it is not a detection-only or read-only permission. `offline_access` allows refresh. The six connector tools restrict the workflow surface, but do not narrow the underlying OAuth grant. Obtain the account owner's consent accordingly. Only request profile/email scopes if an observed Microsoft requirement makes them necessary.

Create the matching OAuth registration with the official toolkit. The current Developer Portal form incorrectly requires a client secret for public PKCE clients; the toolkit accepts the secret-free configuration:

```sh
# Set RESEMBLE_OAUTH_CLIENT_ID to the actual dedicated Resemble public client UID.
atk provision --folder copilot --env dev
```

`copilot/m365agents.yml` registers only the OAuth configuration, restricted to the current Microsoft tenant. It does not deploy or publish the app. The returned vault ID is saved in the ignored `copilot/env/.env.dev`; preserve it to avoid creating duplicate registrations. View the resulting record in Teams Developer Portal → Tools → OAuth client registration:

| Setting | Value |
|---|---|
| Registration name | Resemble AI Authenticity |
| Base URL | `https://mcp.resemble.ai/cowork/mcp` |
| Client ID | Actual UID from the dedicated Resemble application |
| Client secret | None for the public PKCE client |
| Authorization endpoint | `https://app.resemble.ai/oauth/authorize` |
| Token / refresh endpoint | `https://app.resemble.ai/oauth/token` |
| Scope | Three separate scopes: `openid`, `api`, `offline_access` (comma separated in toolkit/portal configuration) |
| PKCE | Enabled |
| App restriction | Any Teams app, per Microsoft's MCP guidance |
| Organization restriction | My organization for initial testing; Any Microsoft 365 organization for approved cross-tenant distribution |

Microsoft's registration ID is **not** the Resemble client ID. Put the Microsoft registration ID in `RESEMBLE_OAUTH_REFERENCE_ID` and run:

```sh
.venv/bin/python copilot/build.py
```

Without that ID, release packaging fails. `--draft` builds `dist/resemble-cowork-DRAFT.zip` with an explicitly unconfigured reference, suitable only for offline review. Do not sideload or submit that draft as a working plugin.

The gateway validates the bearer against Resemble `/api/v2/account` on every MCP request and forwards it only to Resemble's fixed API origin. Tokens and account responses are not stored or returned. Upstream redirects are not followed. There is no service key or tenant-wide credential. Resemble remains responsible for token scope, selected-team authorization, revocation, and media-intake download safeguards. API keys remain accepted for development smoke tests; Microsoft uses OAuth.

## Required end-to-end acceptance

After deploying the connector and configuring OAuth, use a licensed work account with Cowork and custom-app installation enabled:

1. Run `atk auth login m365`, then `atk validate --package-file copilot/dist/resemble-cowork-1.0.0.zip --validate-method validation-rules`. This is Microsoft service validation, which requires sign-in; local schema checks do not replace it. Microsoft requires the major app version to be at least 1, including development candidates.
2. Run `atk install --file-path copilot/dist/resemble-cowork-1.0.0.zip --scope Personal`. Record its actual TitleId and AppId. Do not install tenant-wide for a personal test.
3. Open Cowork → Sources & Skills → Plugins. Confirm Resemble appears and enable it.
4. Connect the dedicated Resemble account through Microsoft's OAuth flow. Verify the publisher, callback, permissions, selected team, and successful return to Cowork. Confirm the public PKCE exchange works in this host; do not infer it from discovery metadata.
5. Ask: “Use Resemble to check this image: https://mcp.resemble.ai/static/logo-square-green.png. Report the detection UUID, status, label and score.” Verify the tool trace and a completed live job, not a model-generated answer.
6. Attach a purpose-made synthetic WAV and ask the same question. Verify Cowork's file-path mapping, byte delivery, one submission, and completed result. Repeat with a small MP4 and verify both audio and video evidence.
7. Ask to analyze a generated 50-word passage. Confirm prediction and confidence are not confused, and no judgment is made while pending.
8. Ask: “Explain the completed media result and its limitations.” Verify question submission and answer retrieval through the plugin.
9. Revoke the Resemble connection, then retry. Verify access is denied. Reconnect and confirm refresh behavior after access-token expiry without exposing tokens.
10. Save screenshots and redacted tool traces, the package SHA-256, Microsoft IDs, job IDs, and the account's tested entitlement context. Mark host E2E passed only after these checks succeed.

For a temporary development host, set `COWORK_PUBLIC_ORIGIN` to its exact HTTPS origin **before starting** the service, update the connector URL and Microsoft OAuth base URL together, and keep authentication enabled. Production should use the existing Resemble-owned host. Do not expose an unauthenticated key-bearing proxy to make a demo work.

## Publication

An official public listing requires owner approval, a deployed Resemble service, successful Microsoft-host testing, and Partner Center submission/review. Prepare the listing using the manifest descriptions and official icons, the linked Resemble privacy/terms pages, support details, screenshots from the actual host, and reviewer test-account access through a secure channel. Do not claim certification, marketplace availability, detection accuracy, or an uptime SLA from this package alone.

## References

- [Microsoft Cowork plugin development](https://learn.microsoft.com/en-us/copilot/cowork/cowork-plugin-development)
- [Microsoft OAuth configuration](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/plugin-authentication-oauth)
- [M365 v1.29 schema](https://developer.microsoft.com/json-schemas/teams/v1.29/MicrosoftTeams.schema.json) — vendored in `schema/` for repeatable offline checks; retrieved 2026-10-27.
- [Resemble documentation](https://docs.resemble.ai)
- [Resemble OAuth discovery](https://app.resemble.ai/.well-known/oauth-authorization-server)
