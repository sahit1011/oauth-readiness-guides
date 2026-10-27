# Setup attempts: checklist

Real setup attempts on free accounts are the ground truth this project checks agent guides against.
Each attempt records what the console actually showed, so a guide's claims can be marked correct,
corrected, or still unverified in [VERIFICATION.md](../VERIFICATION.md).

Rules for every attempt:

- Use a free personal account. Never pay, never submit an app for real review, never accept terms
  on behalf of an organization.
- Record what you **see**, not what you expect. Copy exact field names, limits, and warning text.
- Note the wall-clock time each part took.
- Take screenshots of anything surprising (warnings, caps, required fields) and save them under
  `docs/attempts/<app>/`. Crop out personal data, client secrets, and account emails before saving.
- Never paste a client secret anywhere, including notes. The client ID may be noted as "obtained".

## Record template (copy one per app)

```
App:
Date:
Account type used:
Started at / finished at:

1. Where app registration starts (exact menu path):
2. Required fields on the registration form (exact labels):
3. Redirect URI rules shown (https only? localhost allowed? how many?):
4. Could you authorize your own account immediately? (yes/no, what screen appeared):
5. Warnings or "unverified app" screens shown to the user at consent:
6. User caps shown (test users, installs, workspaces):
7. What the console says is needed before anyone else can connect:
8. Anything that blocked you or needed information you didn't have:
9. Time spent (hands-on):
10. Surprises compared with the agent's guide:
```

## GitHub (expected: minutes)

1. Settings → Developer settings → OAuth Apps → New OAuth App.
2. Register with Homepage URL `https://example.com` and the Composio callback URL from the guide.
3. Generate a client secret (do not copy it anywhere), note that the ID was obtained.
4. Open `https://github.com/login/oauth/authorize?client_id=<ID>&scope=repo` while signed in and
   record the consent screen, including any warning about the app.
5. Do not authorize if the screen asks for more than you're comfortable with; the screen itself is
   the observation.

## Google / Gmail (expected: testing today, verification for production)

1. Google Cloud Console → create a project → APIs & Services → enable the Gmail API.
2. Google Auth Platform (OAuth consent screen): choose the user type. Record whether "Internal" is
   available on a personal account.
3. Add scopes `gmail.readonly` and `gmail.send`. Record the sensitivity label the console gives each
   (non-sensitive / sensitive / restricted) and any text about verification or security assessment.
4. Audience page: record the test-user cap text and the "publish app" requirements.
5. Create an OAuth client (Web application) with the Composio redirect URI.
6. Authorize your own account through the authorize URL and record the "unverified app" screen.

## Slack (expected: instant for your workspace)

1. api.slack.com/apps → Create New App → note both options (From scratch / From an app manifest).
2. OAuth & Permissions: add redirect URL and a bot scope such as `channels:read`.
3. Install to your own workspace and record what happens.
4. Manage Distribution: record the checklist shown before public distribution, and any mention of
   Slack Marketplace review or rate limits for non-Marketplace apps.

## Notion (expected: public connection, check whether review applies)

1. notion.so/my-integrations (or the current developer portal) → New integration.
2. Record the integration types offered (internal / public) and what a public integration requires
   (company name, website, privacy policy, terms, support email).
3. Record whether anything says the integration must be reviewed before other workspaces can install it.
