# Quote API

The complete creation procedure is in [SKILL.md](../SKILL.md). No additional reference is needed for basic quote creation.

Use Headless `dispatch` with `POST /services/data/v68.0/connect/rev/sales-transaction/actions/place`, `userType: business`, and a JSON body. The direct REST route is live-tested. Do not use the former Python/Apex/Tooling adapter.
