Clean conditional design verdict.

The three prior design findings are resolved at the preimplementation-contract level:

- `market-route-ledger.csv` has exactly 40 expected route×market rows, no duplicate route-market pairs, no missing expected pairs, and no page-specific volume/KD/SV claim. Every row is explicitly `Ahrefs credit-limit pending`, with prior broad seed provenance only.
- The final spec section converts UX-01 into a release hold if first-screen route discovery or hub/sales reachability fails: `preimplementation-spec.md` (historical reviewed source: `preimplementation-spec.md`).
- The same section converts UX-05 into a release hold for live manifest, no-JS fallback, supported version/OS, and guide-command disagreement, and correctly treats the `0.5.45` fallback as suspected until verified: `preimplementation-spec.md` (historical reviewed source: `preimplementation-spec.md`).

No unresolved actionable design findings remain from my three conditional-verdict items. This is not an implementation, user-study, product-job, or live-production pass.