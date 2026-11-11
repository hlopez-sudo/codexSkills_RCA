# Configure a Salesforce MCP Connection in Codex

This guide configures a Salesforce MCP connection in the Codex desktop app using **Streamable HTTP** and a Salesforce **External Client App (ECA)**.

`YOUR_...` placeholders represent instance-specific values. Terminal commands assume **macOS with zsh**.

## 1. Make Codex available in Terminal

The Codex command-line tool configures OAuth credentials and launches authentication.

Check whether the CLI is available:

```zsh
codex --version
```

If Terminal reports `command not found`, install the standalone CLI using one of these methods.

With Homebrew:

```zsh
brew install --cask codex
```

Or with Node.js and npm:

```zsh
npm install -g @openai/codex
```

Alternatively, desktop installations containing the bundled CLI at the following location can add it to the current Terminal session:

```zsh
export PATH="/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS:$PATH"
```

To preserve that bundled-CLI PATH setting for future Terminal windows:

```zsh
echo 'export PATH="/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify availability:

```zsh
codex --version
codex mcp --help
```

[Official Codex installation instructions](https://learn.chatgpt.com/docs/codex/cli)

## 2. Create the External Client App in Salesforce

The ECA registers the OAuth application and defines its permitted scopes and callback addresses.

In the target Salesforce org:

- Open **Setup → External Client App Manager → New External Client App**.
- Complete the basic information and enable OAuth.
- Enter this temporary Callback URL:

  ```text
  http://localhost:8080/callback
  ```

- Add these OAuth scopes:
  - **Access MCP servers** — `mcp_api`
  - **Perform requests at any time** — `refresh_token`
- Enable **Issue JSON Web Token (JWT)-based access tokens for named users**.
- Configure additional security settings according to organizational requirements.
- Save the app.
- Open **Consumer Key and Secret** to retrieve both values.

The **Consumer Key** is the OAuth client ID. The temporary callback permits ECA creation before the final Codex callback is known; it must be replaced before authentication completes.

Existing callbacks must be preserved when reusing an ECA. ECA availability can take up to 30 minutes. [Salesforce ECA setup](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/create-external-client-app.html)

## 3. Add the MCP server in Codex

This establishes the server’s address and transport type. Adding the server does not authenticate a Salesforce user.

Open **Settings → MCP servers**. Some versions place this under **Settings → Plugins → MCP**.

| Field | Value |
|---|---|
| Name | `salesforce_mcp` |
| Type | **Streamable HTTP / HTTP** |
| URL | `YOUR_SALESFORCE_MCP_URL` |
| Bearer token environment variable | Leave empty |
| Headers | Leave empty |
| Headers from environment variables | Leave empty |

Save the server.

The CLI command in the next step configures the same named server and supplies its OAuth credentials. Creating the server through the CLI also makes the initial UI entry optional. [Desktop MCP setup](https://learn.chatgpt.com/docs/extend/mcp#configure-in-the-chatgpt-desktop-app)

## 4. Save the ECA credentials through Terminal

The client ID and secret identify the registered application during OAuth. The subsequent browser sign-in identifies the Salesforce user.

Collect the values through Terminal prompts:

```zsh
read "SF_MCP_URL?Salesforce MCP URL: "
read "SF_CLIENT_ID?Salesforce Consumer Key: "
read -s "SF_CLIENT_SECRET?Salesforce Consumer Secret: "
echo
```

Secret entry remains hidden. Save the values in Codex:

```zsh
codex mcp add salesforce_mcp \
  --url "$SF_MCP_URL" \
  --oauth-client-id "$SF_CLIENT_ID" \
  --oauth-client-secret "$SF_CLIENT_SECRET"
```

The server name must match the UI entry. Codex saves the credentials in its local configuration.

If authentication starts automatically, record the displayed callback URL and cancel the incomplete login with **Control+C**. The final callback must be registered before authorization completes.

Clear the temporary shell variables:

```zsh
unset SF_MCP_URL SF_CLIENT_ID SF_CLIENT_SECRET
```

The credentials remain saved in Codex’s configuration.

## 5. Identify the callback URL

This is the address Salesforce uses to return the OAuth authorization result to Codex. It must match a callback registered in the ECA.

Locate the callback displayed by Codex. If necessary, inspect and URL-decode the `redirect_uri` parameter in the generated Salesforce authorization URL.

A callback containing a server-specific ID has this general structure:

```text
http://127.0.0.1:PORT/callback/YOUR_CALLBACK_ID
```

For a fixed localhost callback, retain the generated path and callback ID, if present:

```text
http://localhost:8080/callback/YOUR_CALLBACK_ID
```

If the generated callback has no ID, retain its path without adding an ID.

A fixed localhost port is a configuration choice for this guide. Different MCP endpoint URLs can produce different callback IDs. [Codex callback configuration](https://learn.chatgpt.com/docs/extend/mcp#oauth-client-registration-and-callbacks)

## 6. Save the final callback in Salesforce

This permits Salesforce to return the OAuth result to the exact local address configured in Codex.

Edit the ECA’s **Callback URL** and replace the temporary entry with the final callback, for example:

```text
http://localhost:8080/callback/YOUR_CALLBACK_ID
```

Preserve callbacks used by other connections and save the ECA.

## 7. Save the callback, listener port, and scopes in Codex

This makes Codex’s settings agree with Salesforce’s registered callback, fixes the local listener port, and limits authentication requests to the required scopes.

Open the configuration file:

```zsh
nano ~/.codex/config.toml
```

Update the existing server sections:

```toml
[mcp_servers.salesforce_mcp]
url = "YOUR_SALESFORCE_MCP_URL"
scopes = ["mcp_api", "refresh_token"]

[mcp_servers.salesforce_mcp.oauth]
client_id = "YOUR_CONSUMER_KEY"
client_secret = "YOUR_CONSUMER_SECRET"
callback_url = "http://localhost:8080/callback/YOUR_CALLBACK_ID"
callback_port = 8080
```

The callback path must match the value determined in Step 5. Credentials already saved by the CLI should remain intact.

**Existing sections must be edited rather than duplicated.** The port in `callback_url` and `callback_port` must match for this direct localhost setup.

Save with **Control+O**, press **Enter**, and exit with **Control+X**. The configuration file contains credentials and must remain private.

## 8. Sign into the target Salesforce org

Establishing the correct browser session ensures authorization targets the org containing the ECA.

Log out of other Salesforce orgs in the default browser. Sign into the org containing the ECA and keep the browser open.

This avoids cross-org authorization errors. [Salesforce login preparation](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/log-into-org.html)

## 9. Authenticate the MCP

Codex starts OAuth, Salesforce obtains user authorization, and Codex exchanges the returned authorization code for tokens.

Run:

```zsh
codex mcp login salesforce_mcp \
  --scopes mcp_api,refresh_token
```

Complete the browser authorization flow and wait for **Terminal to confirm successful login**.

The `--scopes` option selects scopes for this login. The saved `scopes` setting supplies them for subsequent authentication attempts. [Codex OAuth configuration](https://learn.chatgpt.com/docs/extend/mcp#oauth-client-registration-and-callbacks)

## 10. Restart Codex and verify the connection

Restarting loads the updated configuration; a live MCP request verifies that authentication works.

Fully quit the desktop app with **⌘Q**, reopen it, and check `/mcp`.

Request a small **read-only operation through the Salesforce MCP**. A successful tool response confirms the connection works; an “enabled” status alone does not.

## 11. Reauthenticate through settings when needed

This renews user authorization for the existing connection without recreating the MCP server or ECA.

Open **Settings → MCP servers**, or the version-dependent **Settings → Plugins → MCP** path.

Locate `salesforce_mcp`, select **Authenticate** when sign-in is required, and complete Salesforce authorization using the org containing the ECA.

Verify the connection with a read-only MCP request. [Desktop authentication instructions](https://learn.chatgpt.com/docs/extend/mcp#configure-in-the-chatgpt-desktop-app)

Terminal provides an alternative:

```zsh
codex mcp login salesforce_mcp \
  --scopes mcp_api,refresh_token
```

The saved callback URL and listener port remain in effect.

## Troubleshooting

| Error | Action |
|---|---|
| `codex: command not found` | Complete Step 1 and verify `codex --version`. |
| Invalid or excessively long `scope` | Retry with `--scopes mcp_api,refresh_token` and inspect the generated URL. |
| `redirect_uri_mismatch` | Match Salesforce’s callback to the decoded request value exactly, including host, port, path, and any callback ID. |
| HTTP callback rejected for `127.0.0.1` | Configure the matching `localhost` callback in both Salesforce and Codex. |
| Cross-org authorization blocked | Sign into the org containing the ECA, then start a fresh login. |
| Browser reports completion but MCP remains unauthenticated | Check Terminal’s final result, restart Codex, and test a live tool request. |
| Local callback port is unavailable | Select an available port and update Codex’s callback URL, listener port, and Salesforce’s registered callback. |
| Connecting another MCP through the same ECA | Configure a separate server name and register its generated callback. |

If a fresh authorization URL still contains an incorrect scope list, replace only its `scope` value with `mcp_api+refresh_token` as a troubleshooting step. All other parameters—including `state`, `code_challenge`, and `redirect_uri`—must remain unchanged, with the corresponding Terminal login still waiting.
