# Gmail setup for the local pilot

Gmail is optional. Greenhouse and manual imports work without Google credentials.
The initial delivery used synthetic tokens, messages and responses. On 22 September
2026 the operator confirmed a successful live account connection after the network
fallback correction described below. Mailbox import requires selecting a label and
enabling checks separately; connection alone does not validate imported alerts.

## Create the local client

1. Create or select a Google Cloud project and enable the Gmail API.
2. Configure the OAuth consent screen for your own testing and add your Google account
   as a test user. Request only `https://www.googleapis.com/auth/gmail.readonly`.
3. Create an OAuth client of type **Web application**. Register exactly
   `http://127.0.0.1:5173/` as an authorised redirect URI, including the trailing slash.
   Use the same host when opening JobHunter AI; `localhost` is a different origin.
4. Download the client JSON outside the repository, then run from the project root:

   ```powershell
   uv run --project apps/api python scripts/configure_gmail.py C:/path/to/client.json
   docker compose up --build --detach --wait
   ```

   The script imports credentials into ignored `.env`, generates a Fernet encryption
   key only when absent and never prints secrets. Keep a private backup of that key:
   replacing it makes saved tokens unreadable and requires reconnection. Custom local
   ports require `--redirect-uri`, matching Google settings and `WEB_PORT`.
5. In Gmail, create a custom label such as **JobHunter alerts**. Apply it only to vacancy
   alerts you want this application to read. The application does not create labels,
   modify messages, mark messages as read or send email.
6. Open **Discover opportunities → Manage sources**, add Gmail and connect it. After
   Google's consent screen, choose the custom label, confirm the source review and
   enable daily checking. Connection alone does not start mailbox reads.

Google grants read-only access at mailbox level; it does not provide a scope limited
to one label. JobHunter enforces the label restriction in its reader and checks each
message's current labels before storing it. Read-only scope is a restricted scope;
Google's testing, token expiry and verification requirements apply. This local pilot
does not establish readiness for distributing a verified Google application.

## Behaviour and limits

The initial check reads at most 20 labelled messages. Later checks read the newest
page and, when available, one older page, up to 40 unique messages with a 60-second
overall deadline. This keeps current alerts visible while progressing through a small
backlog. A large label may take several daily checks and is outside the pilot's scale.
Only complete successful batches advance the cursor. A deleted label disables the
source. Missing emails never imply that an advertised vacancy is closed.

Attachments are ignored. Email bodies are rendered as text; links are listed for
explicit review and are never fetched by the email reader. An email can describe many
jobs, so it is never automatically converted into a single vacancy. Choose one advert
link and explicitly authorise the existing import/extraction flow. No mailbox content
is sent to an AI provider during synchronisation.

OAuth uses a ten-minute, single-use state bound to the authenticated local session,
PKCE and a same-origin, CSRF-protected POST for code exchange. Google redirects to the
frontend root; the frontend removes OAuth query values before completing the exchange.
The session cookie remains SameSite=Strict. Access and refresh tokens are encrypted in
the database, outside records, exports, audit payloads and browser storage. Expired
access tokens are refreshed on demand.

**Disconnect Gmail** pauses the source and erases local OAuth credentials, then attempts
Google revocation. If revocation cannot be confirmed, remove the application's access
in your Google account. Already imported alerts remain in your private local export;
disconnecting is not data erasure. The existing account erasure command removes discovery
records and secrets as well. Do not include mailbox exports in a public repository.

## Connection troubleshooting

Successful OAuth consent does not mean the Gmail API is enabled. If the application
asks you to enable it, open the [Gmail API library page](https://console.cloud.google.com/apis/library/gmail.googleapis.com),
select the project that owns the configured OAuth client and enable the API. Allow
time for the setting to propagate, then select **Load Gmail labels** again. Existing
credentials remain connected; this configuration error does not require a new login.

If Google returns to the application but connection fails, start a new sign-in after
resolving the cause. OAuth state and authorisation codes cannot be reused by reloading
the callback. Check that the registered redirect exactly matches the configured local
address and that the selected Google account is an allowed test user.

The connector tries the DNS-validated addresses within one connection deadline. This
supports Docker installations without IPv6 routing when Google also supplies an IPv4
address. Address fallback happens before sending the HTTP request; an OAuth POST is
never automatically replayed. TLS hostname verification and private-address rejection
remain enforced. Network/temporary provider failures have distinct feedback from
rejected authorisation. No credentials or provider response bodies are logged.

## References checked on 20 September 2026

- [Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)
- [List messages and label filters](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list)
- [Read a message](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get)
- [List labels](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels/list)
