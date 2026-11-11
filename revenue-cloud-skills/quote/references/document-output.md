# Requested usage-tier proposal PDF

“Show me the proposal” requests fresh generation from the saved quote. Reuse the unambiguous current quote and its completed pricing verification. An explicit existing process/file request or unfinished request means retrieve/resume, never generate again. Do not create or modify a quote for a document-only request.

## The one selected proposal

Generate only `RLM_QuoteProposal_CS`, the proposal with usage rate tiers. The user explicitly selected this template; do not search for an alternative, choose a namesake, or fall back to a generic quote document.

| Configured identity | Required value |
|---|---|
| Org ID | `00Dbm0000155DCXEA2` |
| DocumentTemplate ID | `2dtbm000001diaAAAQ` |
| Template name | `RLM_QuoteProposal_CS` |
| TokenMappingMethodType | `ContextService` |
| ContextDefinitionName | `RLM_QuoteDocGenContext` |
| ContextMappingName | `QuoteDocGenMapping` |
| CustomClassName | `RLM_QuoteUsageFormatting` |
| Verified source ContentVersion | `068bm00000S8TXlAAN` |

These are the selected document's org-scoped identifiers, not defaults for other orgs. The helper checks this exact active template and configuration, then resolves its current Original source version for every fresh request. Stop if the template is unavailable or its configured context/formatter differs. Other templates/orgs need an explicit separately verified configuration change.

The current baseline restores the original QuantumBit branding: file version 7 is byte-identical to validated file version 5 (`068bm00000RbMGXAA3`; SHA-256 `199c4c57fec515c8c940337d1bc50641a24a9c242ac72f1079bd38c27e422b26`). The original baseline produced the eight-tier-table proposal; the restored baseline also generated quote `00000101`, whose five rate entries have no adjustment tiers. Absence of tier tables is expected for that quote. When the source version changes, the helper performs one targeted text check of the generated PDF for the usage section and tier-column headings, and caches successful evidence by org/template/source version in `work/`. It does not assume every quote has eight tables. Failure retains the PDF and process for review without regeneration or substitution.

## Reuse established inputs and transport

Prefer supported Headless MCP operations, reusing already described routes. In this connection, MCP generation at v67.0 was rejected and binary retrieval is unavailable; use the verified v68.0 local REST fallback directly rather than rediscovering/retrying those failed operations. Explain the transport switch once. This is local REST capability, not proof of MCP-only support.

Use only an existing CLI session matching the connected org and authenticated username established through connector/session evidence. Reuse that evidence within the current connection; re-establish it if the connection, identity, or org changes. The helper matches local session metadata on every invocation and pins the explicit username. It does not use the default org, export tokens, or authenticate a new user. An arbitrary record's creator is not proof of the connected identity.

Reuse a completed quote read-back from the current session, after any requested edits. Pass its quote number with `--priced-quote-number` only when that exact quote is verified `CompletedWithPricing`. If this evidence is absent/stale, omit the option and the helper reads the quote once. Do not fetch rates/grants or rebuild context for proposal generation.

The tested v68.0 payload is fixed. Do not repeat schema describe or a live Organization read during routine delivery. A real schema/authentication error warrants targeted diagnosis; it does not authorize another submission. Normal sandbox permissions apply; an explicit proposal request already authorizes generation/download through the matching session.

## Run one continuous generation/retrieval sequence

Use [the helper](../scripts/generate_proposal.py) once with output yielding. Let it resolve inputs, submit, poll, and download without model turns between service calls. Do not read its implementation or the validation history during an ordinary proposal request.

```bash
python3 scripts/generate_proposal.py generate \
  --target-org '<existing matching username or alias>' \
  --expected-org-id '<connected org ID>' \
  --expected-username '<connected username>' \
  --quote-id '<current quote ID>' \
  --priced-quote-number '<number from completed pricing verification>' \
  --state '<workspace>/work/proposal-request.json' \
  --output-dir '<workspace>/outputs'
```

With quote verification reused, the service calls are:

1. Query the exact active template/configuration; query its Original `DocumentTemplateContentDoc.LatestContentVersionId`.
2. POST once to `/services/data/v68.0/sobjects/DocumentGenerationProcess`.
3. Query `DocumentGenerationProcess` by the process ID through `GET /services/data/v68.0/query` until Success. Select only Id, Status, ReferenceObject, DocumentTemplateId, RequestText, and ResponseText. Poll about every four seconds. This query works in the verified org; direct process-record GET returned 404 during the performance check.
4. Query only ContentVersions returned by that process; select the unique PDF by `FileExtension`, obtaining `ContentSize`.
5. GET `/services/data/v68.0/sobjects/ContentVersion/<pdf-version-id>/VersionData` into the local output file.

The helper preserves this verified generation contract:

```javascript
{
  Type: "GenerateAndConvert",
  ReferenceObject: quoteId,
  DocumentTemplateId: selectedTemplateId,
  DocumentInputType: "DocumentTemplate",
  DocGenApiVersionType: "Advanced",
  DocGenAdditionalInputType: "ContextService",
  DocGenAdditionalInput: quoteId,
  RequestText: JSON.stringify({
    keepIntermediate: true,
    title: uniqueTitle,
    templateContentVersionId: currentSourceVersionId
  })
}
```

`RequestText` is a compact JSON string, at most 255 characters in the verified contract. `DocGenAdditionalInput` is the plain Quote ID. The configured context/formatter supplies usage schedules, tiers, grants, and special terms. No manual token data, separate context-build request, or QuoteDocument insert is needed. `keepIntermediate` retains the service's Word intermediate; only the PDF is downloaded/delivered.

## Keep correctness checks cheap

Journal the exact request before POST and save the returned process ID immediately. Require HTTP 201, `success: true`, and empty errors. Each process read must match the requested quote, selected template, and source version. At Success, parse the returned ContentVersion IDs (15 or 18 characters), select the PDF by extension, and download those exact bytes. The process reference plus returned file IDs establish provenance; omit the separate ContentDocumentLink lookup.

Require a nonempty `%PDF-` signature and exact ContentSize match. Keep the local checksum and journal for safe resume. Binary VersionData requires its own request, not Composite or JSON capture. Preserve the service-generated PDF unchanged.

Routine delivery ends here. Do not invoke the PDF skill, extract all text, render pages, make contact sheets, or inspect layout for a known template version. Use the PDF skill only for an explicitly requested review or investigating a material defect. A new source version uses the helper's targeted text check once, without rendering: `pdftotext`, or `pypdf` in the Python runtime when that executable is absent. If neither is available, resume the same journal using the bundled Python runtime with `pypdf` (locate it with `load_workspace_dependencies` when necessary). The saved PDF is reused; no new generation or download is needed.

## Resume without duplicate generation

- `resume`: pass the same identity and `--state`; optionally change `--output-dir`. It recovers an uncertain POST by exact journaled request, polls the existing process, or resumes download/checking. It never POSTs again.
- `retrieve`: pass the same identity plus `--quote-id`, `--process-id`, a new `--state`, and `--output-dir`. It verifies the process is for the selected proposal and retrieves its PDF without fresh template lookup or generation.
- `--wait-seconds`: default 45, allowed 0–55. `pending` means resume the same journal when continuing. Waiting/InProgress is not a failure; partial Word output is not the finished PDF. Failure/Blocked/unknown status retains the process and diagnostic.
- A timeout, 5xx, or malformed POST success is uncertain. Resume one exact matching journaled request; never blindly resubmit. A definite rejection is reported without retry. Existing journals and locks prevent accidental duplicate submissions.
- Inspect `outcome`: exit 0 can mean pending or downloaded. Downloaded results include the path, IDs, size, hash, per-stage timings, and API-call count. Each fresh helper invocation checks identity locally; successful output must still be attached in Codex.

## Attach immediately

When `outcome` is `downloaded`, attach the actual PDF immediately:

```text
:codex-file-citation{path="<verified absolute PDF path>" purpose="output"}
```

Use the applicable source-file form for an unchanged previously generated PDF. Do not substitute a browser, Salesforce record/viewer link, screenshot, or reconstructed document. A failed attachment needs republication of the existing file, not regeneration.

Target only a few seconds between completed download and attachment. Service generation latency varies; use the helper's timings to distinguish preparation, submission-to-observed-success, retrieval, and total invocation time. See [validation evidence](validation.md#proposal-performance-update---november-3-2026) only for maintenance.

## API references

- [DocumentGenerationProcess](https://developer.salesforce.com/docs/revenue/clm-developer/guide/sforce-api-objects-documentgenerationprocess.html)
- [Context Service inputs](https://help.salesforce.com/s/articleView?id=ind.sf_docgen_con_service_docgen_one.htm&language=en_US&type=5)
- [Binary sObject Blob Get](https://developer.salesforce.com/docs/platform/api-rest/guide/resources-sobject-blob-retrieve.html)
