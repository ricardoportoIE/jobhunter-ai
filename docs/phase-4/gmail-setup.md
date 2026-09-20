# Gmail setup for the local pilot

Gmail is optional. Greenhouse and manual imports work without Google credentials.
No Gmail account was connected during implementation: the project owner has not yet
created an OAuth client. Automated tests use synthetic tokens, messages and responses.

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

## References checked on 20 September 2026

- [Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)
- [List messages and label filters](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list)
- [Read a message](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get)
- [List labels](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels/list)
