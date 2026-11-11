# Direct REST validation — October 22, 2026

The basic quote-creation procedure uses Headless POST `/services/data/v68.0/connect/rev/sales-transaction/actions/place`. Basic quote creation does not use Python, Apex or the Tooling API.

## Measured live creation

[Quote 00000032](https://trailsignup-22f202b7c11721.my.salesforce.com/lightning/r/Quote/0Q0bm000003qeIzCAI/view), Pied Piper:

- GPT Enterprise Monetary Commit: quantity 500.
- Additional API: quantity 2.
- Term: October 22, 2026–October 21, 2027.
- Annual billing, resolved USA Advance treatment.
- Both products in one POST, with usage catalog fetch included.
- HTTP 201, `isSuccess: true`, empty errors, returned quote ID.
- One read-back confirmed both lines, quantities, dates, billing fields and `CompletedWithPricing`.
- Priced total: USD 30,000. Commitment amounts were not queried or changed.

| Measured step | Seconds |
|---|---:|
| Parallel account, product-with-pricebook-entries and billing-treatment reads | 1.800 |
| One Place Sales Transaction POST | 3.482 |
| One read-back | 1.114 |
| Complete single-orchestration tool sequence | **6.396** |

This timing measures the live tool sequence, not file editing or a guaranteed future chat latency. An earlier test, [quote 00000031](https://trailsignup-22f202b7c11721.my.salesforce.com/lightning/r/Quote/0Q0bm000003qeFlCAI/view), also succeeded with the same two product quantities. Its POST took 3.304 seconds; the lookup-through-read-back sequence took 33.813 seconds including a model turn between calls. Combining dependent calls removed that overhead.

Both new quotes are labeled TEST and remain Draft. No approval, order, activation or catalog change occurred.

## Other coverage

Earlier quotes 00000029 and 00000030 tested annual/monthly terms, quantity/discount changes, add/remove, commitment and tier changes through the old Apex transport. Those records remain evidence of field semantics, not validation of the retired transport for the active connection. Direct REST creation is verified above; individual optional edit graphs were not re-exercised in this revision.

Required bundles, one-time/evergreen transactions, prorated terms, multi-currency, flat rates, large graphs and asynchronous execution were not part of this test. These do not trigger extra preflight work for the tested basic creation path.

## Proposal output validation - November 3, 2026

**Verified scope:** fresh Context Service proposal generation via authenticated local Salesforce CLI REST v68.0, process polling, PDF identification and quote association through MCP reads, binary download through local REST v68.0, local integrity/render checks, and delivery as a downloadable artifact in Codex. **MCP-only generation and binary download remain unverified.** These results establish one successful same-user workflow, not every user's entitlements or every template.

### Earlier MCP-only attempt

Test org: `trailsignup-22f202b7c11721`. Connected identity: `005bm00000ZmsUzAAJ`. Earlier quote: `0Q0bm000003y3hFCAQ` (00000057). All IDs below are evidence only; runtime instructions resolve inputs dynamically.

- MCP v67 SOQL resolved the quote, active `RLM_QuoteProposal_CS` template, original file junction, and current template ContentVersion.
- DGP describe reported the object and payload fields createable, including Context Service inputs. Actual statuses were InProgress, Success, Failure, Blocked and Waiting.
- A Headless POST to `/services/data/v67.0/sobjects/DocumentGenerationProcess` returned HTTP 400 `FUNCTIONALITY_NOT_ENABLED`: `insert is not supported for entity type 'DocumentGenerationProcess'.` It returned no process ID and was not blindly retried.
- The described `/services/data/v64.0/automation/actions` catalog returned HTTP 403 `FUNCTIONALITY_NOT_ENABLED` for `InvocableActionsApiFamily`; no action was invoked.
- Discovery exposed no verified authenticated binary-download operation/resource. A VersionData path was metadata, not downloaded bytes. A queued `open_in_codex` request established neither visible rendering nor downloadable delivery.

These are dated, route-specific observations. They do not establish that Salesforce REST generation is unavailable or identify the cause of the MCP rejection.

### Successful v68.0 local REST workflow

The user requested verification of the documented v68.0 path. The transport switch was explained before using the existing local session. The CLI session matched the connected org and username; no different identity, fresh login, permission assignment, org-setting change, Apex deployment, or public file link was used.

| Evidence | Verified value |
|---|---|
| Org ID | `00Dbm0000155DCXEA2` |
| Username | `trailsignup.22f202b7c11721@salesforce.com` |
| Quote | `0Q0bm000003y9Y9CAI` / 00000084 / GPT Enterprise for Global Media |
| Active template | `2dtbm000001diaAAAQ` / RLM_QuoteProposal_CS / ContextService |
| Original template version | `068bm00000RbMGXAA3` |
| Generation process | `0nnbm000000A817AAC` |
| Request title | `Quote-00000084-20261103T193931Z` |
| Submitted at | November 3, 2026, 19:39:31 UTC |
| PDF version | `068bm00000RbeLWAAZ` |
| PDF document | `069bm00000TznPiAAJ` |
| Word version | `068bm00000RbYeIAAV` |
| PDF byte count | 91,729, exactly matching ContentSize |
| PDF format | PDF 1.7, 5 letter-size pages, not encrypted |
| PDF SHA-256 | `cdfd7fa92f797953b10bd59ba65537be1c6958c3fedac09e9f9bba0df4e76b20` |

1. MCP reads confirmed the quote was `CompletedWithPricing`, resolved the template and its current original file, and corroborated the identity of the quote just created through this connection.
2. Local REST `GET /services/data/v68.0/sobjects/DocumentGenerationProcess/describe` returned HTTP 200. The request fields and picklist values matched the schema.
3. Local REST `POST /services/data/v68.0/sobjects/DocumentGenerationProcess` returned HTTP 201, `success: true`, empty errors, and the process ID above. The request used GenerateAndConvert, Advanced, DocumentTemplate, ContextService, the plain quote ID as additional input, and a compact JSON RequestText with keepIntermediate, title, and templateContentVersionId.
4. A v68.0 process GET returned InProgress with only the Word version in ResponseText. A later MCP read confirmed Success with `068bm00000RbYeI,068bm00000RbeLW`. The partial response was not mistaken for completion.
5. MCP ContentVersion reads selected the PDF by extension. ContentDocumentLink confirmed its association with the requested quote.
6. `sf api request rest /services/data/v68.0/sobjects/ContentVersion/068bm00000RbeLWAAZ/VersionData --target-org <matching-username> --stream-to-file <output-path>` downloaded the PDF. The CLI stream path did not expose an HTTP status, so success was established by the actual bytes, metadata-size match, PDF parsing, and rendering; do not claim a measured HTTP 200 for this download.
7. The file began with `%PDF-1.7`, matched ContentSize, parsed as five pages, and rendered for inspection. Its content included Global Media, quantity 500, and term November 3, 2026–November 2, 2027. The exact service-generated PDF was delivered using a Codex output file citation.

The request created the generation process and its output files. Quote commercial values and template/context configuration were not edited. The workflow did not depend on inserting a QuoteDocument record.

### Reusable helper validation

The packaged helper generalizes the proven transport with dynamic runtime inputs and identity matching.

- Eleven fixture tests passed using a mocked Salesforce CLI transport, including HTTP error envelopes, successful submission/download, reuse of a downloaded result, partial InProgress output, Waiting/Blocked/Failure/unknown states, ambiguous-POST recovery with exact request matching, no-match recovery without resubmission, definite rejection without retry, identity/schema mismatch before POST, retrieval without generation, quote/file association checks, HTML/truncated download rejection and recovery, and concurrent-journal locking.
- A live read-only `retrieve` run of the new helper used the process above. It verified the matching existing session and live org ID, read Success through v68.0, resolved the PDF and its quote link, and downloaded 91,729 bytes with the same SHA-256 shown above. It created no generation process or Salesforce record.
- The helper's new-generation branch was tested with fixtures; the earlier live generation used the predecessor verification script. These are distinct evidence scopes.
- The skill package is checked with the skill-creator validator and relative-reference checks before installation.

Post-negotiation generation, non-admin identities, other template mapping methods, and MCP-only generation/download are outside this live test. Local REST success must not be generalized to those cases. Browser and Salesforce-link substitutions remain outside the requested delivery workflow.


## Proposal performance update - November 3, 2026

The user selected only `RLM_QuoteProposal_CS`, the proposal with usage tiers, and authorized removing routine overhead. This revision specializes the document branch to that exact org/template; the earlier helper validation above describes the previous implementation. Basic quote creation and negotiation are unchanged.

- A live MCP read confirmed template `2dtbm000001diaAAAQ` is Active, uses ContextService, context `RLM_QuoteDocGenContext`, mapping `QuoteDocGenMapping`, and formatter `RLM_QuoteUsageFormatting`. The new helper's two input-resolution queries also passed against the live org and resolved the baseline source version `068bm00000RbMGXAA3`.
- Reuse completed pricing evidence with `--priced-quote-number`; otherwise perform one quote read. Match the existing CLI identity locally on every invocation. Remove the routine live Organization query, schema describe, and ContentDocumentLink query. Keep the journal, same-process quote/template/source checks, output-ID provenance, PDF signature, byte count, and checksum.
- The warm generation fixture uses six API calls with one completed-status poll: two template reads, one POST, one process query, one ContentVersion query, one binary GET. The old helper used ten with the same polling count. Extra status polls add one call each.
- A live direct GET of the existing process returned CLI `ERROR_HTTP_404`. SOQL returned the same successful process through both MCP and v68.0 local REST. Polling now uses one targeted SOQL query rather than direct process-record GET; it adds no fallback request to normal execution.
- A live read-only resume retrieved process `0nnbm000000A8FdAAK` for quote 00000091 using three API calls. Total helper invocation: **5.714 seconds**; metadata/download phase: **3.287 seconds**. PDF size: **91,703 bytes**, SHA-256 `8db15cf5cf9ee84c47221cfcc446ce0657cef569521936964d78f8030b839598`, exactly matching the already delivered proposal. This measures retrieval, not new-generation or end-to-end chat latency.
- Eighteen fixture tests passed, including template/org/formatter restrictions, warm-call budget, pricing-evidence reuse and fallback, uncertain POST recovery, no duplicate submission, pending/terminal states, source-version mismatch, file corruption, new-version tier checks and scoped cache reuse, and journal locking. Run `python3 -B scripts/test_generate_proposal.py` for maintenance; it makes no network requests.
- The new-version text checker was also exercised on the actual service-generated PDF using the bundled Python runtime's `pypdf` fallback. This environment lacks `pdftotext`. The check passed without rendering; its synthetic-version test cache was isolated and removed.
- Routine delivery now attaches the verified PDF immediately. Rendering, contact sheets and visual inspection are reserved for requested review or defect investigation. A new source version receives a targeted tier-text check once, with successful validation cached by org/template/source version.

No new generation process, quote, template, or other Salesforce record was created/changed during this update. Fresh-generation behavior was tested with fixtures and the existing verified POST contract; the live checks covered input resolution and retrieval. The skill-creator validator and relative-reference checks pass. Timing improvements for a new full generation remain to be measured on the next requested proposal.
