# Resemble AI for Microsoft Copilot Cowork

Resemble-branded Microsoft 365 plugin source, with four skills and seven live-service tools. Version 1.1.0 adds Signal fraud screening and a web-research screening skill. The earlier six authenticity tools completed live OAuth testing in Cowork, including PNG, WAV, and MP4 workspace-file delivery. See [the validation record](VALIDATION.md) for evidence and remaining checks. This is **not a Microsoft-certified or published store listing**.

The plugin checks audio, images, video, and text, screens selected content against Signal fraud categories, and answers questions about completed detection reports. It sends only the inputs selected for a tool call to Resemble. Creation calls can consume credits. It does not send email, change files in Microsoft 365, or create a public media upload.

## What is included

| Component | Purpose |
|---|---|
| `appPackage/manifest.json` | M365 v1.29 manifest with `OAuthPluginVault` connector |
| `appPackage/skills/` | Media authenticity, text authenticity, detection brief, web fraud check |
| `appPackage/color.png`, `outline.png` | Required sizes, derived from the official logo in this repository |
| `../cowork_server.py` | Authenticated Streamable HTTP surface at `/cowork/mcp` |
| `build.py` | Deterministic ZIP, schema/skill/icon validation, missing-registration gate |
| `smoke.py` | MCP SDK test through the running connector to real Resemble APIs |
| `../tests/` | Protocol, errors, upload, auth, result semantics, and packaging tests |

Supported tools are `submit_media_detection`, `get_media_detection`, `submit_text_detection`, `get_text_detection`, `submit_detection_question`, and `get_detection_answer`. Media submissions accept a public HTTPS URL or a file up to 10 MiB. The file schema uses a top-level string with `contentEncoding: base64`, allowing Cowork to supply bytes outside the model context. This mapping was verified with real PNG, WAV, and MP4 workspace files in Cowork.

Version 1.0.1 adds handling for completed audio jobs with no usable scores: `assessment_available` is false, `label` is `unavailable`, and `reported_label` preserves the original upstream label. Null values and negative sentinels cannot establish authenticity. Valid zeros and separate video evidence remain unchanged.

## Signal and automatic web screening

`score_signal_content` sends exact retrieved text or a selected media file to `POST /signal`. Text is limited to 20,000 characters per call and media to 10 MiB. It returns a synchronous `safe`, `suspicious`, or `fraud` verdict with category evidence, a submission ID when provided by the service, and coverage metadata: submitted character/byte count, content fingerprint, and optional public source URL. The source URL is attribution only; the connector does not fetch it or pass it to Signal. Signal stores a team submission and requires the corresponding entitlement. No new OAuth scopes are required.

The `web-fraud-check` skill is described to activate whenever Cowork searches, browses, researches, or summarizes public internet content. It screens the actual source text before relying on it, keeps sources and long-document chunks separate, discloses excerpt-only coverage, and reports failures as not screened. It never treats a safe result as approval to obey page instructions. Private/authenticated pages and internal Microsoft 365 content require the user's authorization before disclosure. Signal has no documented zero-retention option in this tool.

**This is a prompted workflow, not an enforced web interception layer.** Microsoft documents context-based skill selection and says plugin event hooks are unsupported. A plugin cannot guarantee that every built-in web call runs Signal. To reinforce activation across tasks, an owner can add [the supplied custom instructions](COWORK_INSTRUCTIONS.md) to Cowork Preferences. Those instructions still cannot create an enforcement hook or override the host's approval controls. A guaranteed security gate would require a host-supported interception mechanism or a controlled retrieval path used for all browsing.

Signal checks the connected team's configured categories. Its scores are not calibrated fraud probabilities; a safe result does not establish factual accuracy, identity, URL reputation, or absence of prompt injection. Reference examples are not quotes from the source. A page discussing scams can match fraud categories without being a fraudulent page. Live tests reproduced this with a Signal documentation excerpt, so the skill explicitly requires context and coverage caveats rather than automatic blocking.

Signal has no documented per-submission polling endpoint. Calls share the connector's bounded upstream budget. On timeout, the outcome can be unknown: do not automatically retry, silently resubmit, or call the source safe. Check the Resemble dashboard before an authorized retry. The plugin does not expose team-wide submission listings or category/settings mutation.

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

The current Resemble `api` scope is broad customer API access, subject to team permissions; it is not a detection-only or read-only permission. `offline_access` allows refresh. The connector tools restrict the workflow surface, but do not narrow the underlying OAuth grant. Obtain the account owner's consent accordingly. Only request profile/email scopes if an observed Microsoft requirement makes them necessary.

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

1. Run `atk auth login m365`, then `atk validate --package-file copilot/dist/resemble-cowork-1.1.0.zip --validate-method validation-rules`. This is Microsoft service validation, which requires sign-in; local schema checks do not replace it. Microsoft requires the major app version to be at least 1, including development candidates.
2. Run `atk install --file-path copilot/dist/resemble-cowork-1.1.0.zip --scope Personal`. Record its actual TitleId and AppId. Do not install tenant-wide for a personal test.
3. Open Cowork → Customize → Discover. Open Resemble AI, select Install if prompted, and confirm it is enabled with all four skills. Verify the actual version and skill list: toolkit acceptance alone may leave Cowork showing an older acquired version. Older Cowork versions may label this area Sources & Skills → Plugins.
4. Connect the dedicated Resemble account through Microsoft's OAuth flow. Verify the publisher, callback, permissions, selected team, and successful return to Cowork. Confirm the public PKCE exchange works in this host; do not infer it from discovery metadata.
5. Ask: “Use Resemble to check this image: https://mcp.resemble.ai/static/logo-square-green.png. Report the detection UUID, status, label and score.” Verify the tool trace and a completed live job, not a model-generated answer.
6. Attach a purpose-made synthetic WAV and ask the same question. Alternatively, have Cowork create non-sensitive fixtures in its workspace. Verify Cowork's file-path mapping, byte delivery, one submission, and completed result. Repeat with a small MP4 and verify both audio and video evidence. A tone tests transport and unavailable-audio handling, not speech detection. Submit files sequentially: Cowork may reject a second write call while another approval is pending. Only retry a definitively unexecuted call; never automatically retry an uncertain network submission.
7. Ask to analyze a generated 50-word passage. Confirm prediction and confidence are not confused, and no judgment is made while pending.
8. Ask: “Explain the completed media result and its limitations.” Verify question submission and answer retrieval through the plugin.
9. Revoke the Resemble connection, then retry. Verify access is denied. Reconnect and confirm refresh behavior after access-token expiry without exposing tokens.
10. Save screenshots and redacted tool traces, the package SHA-256, Microsoft IDs, job IDs, and the account's tested entitlement context. Report functional host testing separately from refresh/revocation testing and publication approval; do not imply unperformed checks passed.

For Signal, also run an explicit synthetic fraud check and a workspace-media check through the live host. Then start a fresh task with an ordinary public-web research request that does **not** mention Signal or fraud. Record whether the skill activates, the actual retrieved material sent, the returned IDs, and the final coverage note. Repeat with the personal instructions if available, identifying which activation mode was tested. A successful prompted check does not prove automatic selection; a successful automatic-selection sample does not prove universal enforcement.

For a temporary development host, set `COWORK_PUBLIC_ORIGIN` to its exact HTTPS origin **before starting** the service, update the connector URL and Microsoft OAuth base URL together, and keep authentication enabled. Production should use the existing Resemble-owned host. Do not expose an unauthenticated key-bearing proxy to make a demo work.

## Publication

An official public listing requires owner approval, a deployed Resemble service, successful Microsoft-host testing, and Partner Center submission/review. Prepare the listing using the manifest descriptions and official icons, the linked Resemble privacy/terms pages, support details, screenshots from the actual host, and reviewer test-account access through a secure channel. Do not claim certification, marketplace availability, detection accuracy, or an uptime SLA from this package alone.

## References

- [Microsoft Cowork plugin development](https://learn.microsoft.com/en-us/copilot/cowork/cowork-plugin-development)
- [Microsoft OAuth configuration](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/plugin-authentication-oauth)
- [M365 v1.29 schema](https://developer.microsoft.com/json-schemas/teams/v1.29/MicrosoftTeams.schema.json) — vendored in `schema/` for repeatable offline checks; retrieved 2026-10-27.
- [Resemble documentation](https://docs.resemble.ai)
- [Resemble OAuth discovery](https://app.resemble.ai/.well-known/oauth-authorization-server)
- [Signal scoring API](https://docs.resemble.ai/detect/signal/score)
- [Cowork automatic skill selection](https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/cowork-plugins)
- [Cowork personal instructions](https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/cowork-customize)
