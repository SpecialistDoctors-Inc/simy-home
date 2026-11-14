# Registrar automation integration

AuthCode intake creates a durable `clinic-transfer:<subscription>` record in the
same transaction as the authenticated clinic intake. It does not grant a site,
change DNS, or publish content. WordPress remains a separate optional connector.

`domain_transfer.prepare` accepts a **server-built** request bound to the paid
Google subject and domain. Before calling it, the intake layer must obtain the
registrant's administrative/registrant/technical contacts, their renewal choice,
the exact provider quote and acceptance, and trusted DNS continuity evidence.
Never accept `dns_evidence` directly from an unauthenticated/browser claim. A
public A/MX lookup is not a complete zone export. Preserve email, TXT, DKIM, DMARC,
SPF, SRV, CAA and DNSSEC as applicable; verify the migrated zone or continued DNS
service before preparing a registrar move. Do not substitute SIMY's contact for
the customer's registrant identity.

The worker checks the active purchase again before submitting, caps the provider
charge at the accepted amount, records intent before sending, and disables SDK
retries. A lost response is reconciled through all provider operation pages; it
never triggers a second TransferDomain call. Unknown/ambiguous outcomes remain
pending. Registrar success means only domain-registration transfer success.
Customer email/registry approval, locks, unsupported TLDs and third-party service
restrictions cannot be bypassed by this worker.

The scheduler is off by default. Enable it only after the authenticated details,
price acceptance and DNS continuity integration is verified. Its dedicated
Secrets Manager secret contains only the intake encryption key, with the same
value used to encrypt AuthCodes; no Stripe API key is needed by this worker.
The SDK upgrade is required for the provider-side `Consent.MaxPrice` cap.

The draft now includes the authenticated quote/contact form, registrar progress,
complete-import validation/normalization, isolated repository/hosting creation,
paid-owner grant, native-package download and approval-gated DNS publication.
See [CLINIC-ACTIVATION.md](CLINIC-ACTIVATION.md) for configuration and evidence.
These are implemented paths, not live acceptance or enabled production services.

Remaining integration before self-service acceptance:

* Connect the DNS provider or migrate a complete zone and verify continuity.
* Connect dynamic functions (forms, reservations, login, commerce) to their actual
  systems. Copying public HTML does not migrate these functions.
* Test a real authorized domain through the registrar, Mac save, preview and
  the customer's exact-artifact publication approval. Unit/SDK tests are not
  this live acceptance.

Provider contracts:
[TransferDomain](https://docs.aws.amazon.com/Route53/latest/APIReference/API_domains_TransferDomain.html),
[Transferability](https://docs.aws.amazon.com/Route53/latest/APIReference/API_domains_DomainTransferability.html),
[ListOperations](https://docs.aws.amazon.com/Route53/latest/APIReference/API_domains_ListOperations.html).
