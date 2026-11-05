# Dedicated HP connection settings

This standalone service requires no SIMY account/API/WorkFlow. It runs no Codex or
model provider. Existing production remains on the previous accepted release
until real provider/host tests authorize cutover.

## GitHub administrator registration

Keep the webhook inactive until the endpoint, signing secret and exact repository
bindings have been verified. Then enable the declared event set.

Register the private organization-owned `SIMY HP Local Editor` app using
`github-app-registration.json`; install it only on `hp-site-sample-clinic`.
Runtime permissions: Contents and Pull requests write; Checks and Actions read;
Metadata read. No Workflows write, Administration, Members or customer OAuth.
Do not share an operator login or ship the app private key to a customer.

Repository creation and installation selection are administrator setup actions,
separate from the runtime app. Keep existing unrelated organization apps/settings
unchanged. Record app/installation/repository IDs in private operator bindings.
Store the app PEM and a generated webhook secret in a dedicated Secrets Manager
secret. Never put values in Terraform state, SSM command text, repo or output logs.

For a newly created site repository, inspect its Actions page and complete the
repository's **Enable Actions on this repository** activation if shown. The REST
Actions permissions endpoint can report `enabled: true` while this UI activation
is still pending. Verify a normal App-created pull request or synchronize event
starts the trusted workflow and produces its exact-head artifact. A manually
dispatched successful run does not prove automatic validation is working.

## Google identity application

Create a separate Web application OAuth client named `SIMY HP Local Editor` in
the existing authorized Google Cloud project. Redirect URI:
`https://hp-control.simy.one/oauth/google/callback`. Login scopes are openid and
email only. The operator provisions either the verified subject/site mapping
or an expiring invitation for an exact email with explicit site roles. First
Google login claims that invitation once using the verified email and binds the
immutable subject. A reused email cannot claim it again; a disabled existing
principal cannot bypass revocation through an invitation. No email suffix or
sheet actor grants access.

Keep this web client separate from the old Desktop client and the dedicated
operator Drive/Sheets/Gmail credentials. Drive file-transfer requires operator
access to the configured folders; broaden scopes only via explicit operator
consent, never by changing saved credential JSON.

## HP plugin connection

Register the HTTPS MCP endpoint `https://hp-control.simy.one/mcp` with Google-backed
OAuth 2.1 discovery and PKCE. The initial test account is operator-provisioned
privately. Do not publish its Sheet ID, Google subject, recipient, tokens or keys
in this public repository. Test actual desktop rendering/click confirmation
before enabling production. UI-only metadata is not itself authorization proof.

A separate RSA signing key issues audience-bound HP access tokens. Keys are
stored as secret values, with only public JWKs exposed by `/oauth/jwks`.
