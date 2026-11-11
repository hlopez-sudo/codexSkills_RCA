# Revenue Cloud reusable skills

Exported from the live skill folders on November 11, 2026.

Included skills:
- quote: quote creation, negotiation, and proposal PDF generation
- managing-asset-lifecycle: asset inventory, raw journal usage, amendments, renewals, and cancellations
- managing-revenue-conversion: quote-to-order conversion and order activation

Each skill includes its SKILL.md, agents metadata, references, and any scripts/tests. Python bytecode caches are omitted. Source skill files are unchanged.

To reuse locally, extract the three skill folders into the destination skill directory, such as ~/.agents/skills/. Configure the required Salesforce Headless and Revenue Cloud MCP connections in the destination environment. The included agents/openai.yaml files preserve the existing connection definitions; point the org-specific Revenue Cloud URL at the intended org when migrating.

The Quote proposal branch includes the selected org-specific template IDs and local Salesforce session checks. Those settings require verification/configuration for another org; consult quote/references/document-output.md. The helper and its tests are included in quote/scripts/.

The bundle contains skill files, not authenticated sessions or Salesforce templates/metadata deployments. No Salesforce connection is required merely to unpack these files.
