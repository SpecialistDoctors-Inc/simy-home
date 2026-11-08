# Dedicated HP connection settings

The existing operator-granted service works independently of SIMY. Commercial
sites use the SIMY license bridge described below. The control service runs no
Codex or model provider.

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

For a registered ChatGPT callback, the Google callback displays a static
handoff page instead of automatically opening ChatGPT in the Google browser
profile. Copy its “ChatGPTに戻って接続を完了” link into the browser/profile where
the ChatGPT connection was started. This is the same one-time, 120-second code
URL; do not put it in logs, chat, screenshots or shared documents. The original
client state and PKCE verifier are still required. The page has no scripts or
third-party resources and is not cached or framed. Registered loopback CLI
callbacks retain their exact HTTP 302 redirect behavior.

A separate RSA signing key issues audience-bound HP access tokens. Keys are
stored as secret values, with only public JWKs exposed by `/oauth/jwks`.

## Commercial HP sites

Bind a provisioned site to its SIMY billing organization by setting
`license_policy: {"mode":"simy","org_id":"<SIMY organization UUID>"}` in the
operator-owned site record. This extends existing verified Google-subject and
site-role checks. Sites without a license policy retain their existing explicit
operator grants and cannot qualify for the commercial checkout. A billing
organization does not authorize an arbitrary site URL or create provider bindings.

Configure the two bridge directions together. `entitlement_endpoint` identifies
the trusted SIMY `/functions/v1/hp-control-entitlement` URL. The dedicated raw
token at `entitlement_secret_arn` must match the backend's
`HP_CONTROL_ENTITLEMENT_TOKEN`. This read-only check receives the server-owned
organization ID and authenticated Google subject. API and worker checks both
require an affirmative response on each managed action. Unavailable responses
block managed access and queued commands can retry under the same operation ID.

`preflight_secret_arn` holds a separate raw token matching SIMY's
`HP_CONTROL_PREFLIGHT_TOKEN`. Use independent base64url tokens of at least 32
characters. After verifying identity and billing authority, SIMY sends a JSON
`POST /internal/license/preflight` with `org_id` and `google_subject`.
It receives `{"ready":true}` only when that Google principal already has read
and edit permission on an enabled site bound to that organization and the entitlement
lookup responds. This check does not require a paid license or modify authority.
An unclaimed HP invitation must be redeemed through the existing Google
connection before checkout. A negative or unavailable preflight leaves checkout
unavailable until the existing operator site setup or connection is complete.
