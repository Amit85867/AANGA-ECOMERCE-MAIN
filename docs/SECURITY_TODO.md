# Security to-do

Things that need the owner's hands: they touch a real credential, a remote
repository, or an external dashboard, so nothing here has been done
automatically.

## 1. Leaked master-admin password — rotate first, purge second

**What leaked.** An early `backend/.env.example` carried a real admin password
as its `ADMIN_PASSWORD` value. It was later replaced with a placeholder, but
git keeps every version:

| Commit | Date | On GitHub? | Where |
|---|---|---|---|
| `4651da7` | 2026-07-12 | **yes — on `origin/main`** | `backend/.env.example` |
| `8b20d6c` | 2026-07-25 | no (local branch only) | `backend/.env.example` (the line removing it) |
| `5b56e8e` | 2026-07-25 | no (local branch only) | `docs/DEPLOYMENT.md` quoted it in a warning |

The password itself is deliberately not repeated in this file. To see it:
`git show 4651da7:backend/.env.example | grep ADMIN_PASSWORD`.

**Status on 2026-10-10:** the same value is still the `ADMIN_PASSWORD` in the
local `backend/.env`, so the local master admin still uses it. Treat it as
public: anyone who has ever cloned or viewed the GitHub repository has it.

### Step 1 — rotate (do this now; it is what actually fixes the problem)

Purging history does not un-leak a password. Changing it does.

1. Pick a new password (16+ characters, from a password manager). Do not reuse
   the old one anywhere.
2. Put it in `backend/.env` as `ADMIN_PASSWORD`. Nowhere else.
3. Update the stored hash. `ADMIN_PASSWORD` only *seeds* an admin that does not
   exist yet, so editing `.env` alone changes nothing for an existing account:

   ```powershell
   cd backend
   venv\Scripts\flask set-admin-password
   ```

   It reads `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `backend/.env` and rewrites
   the hash (it prompts if `ADMIN_PASSWORD` is unset). `flask seed-admin` will
   not do this — it refuses to touch an account that already exists.

4. Confirm: the old password is refused at `/admin/login`, the new one works.
5. If that password was ever used for anything else (email, Razorpay,
   Supabase, Shiprocket, hosting), change it there too.
6. On every deployed environment, set the new `ADMIN_PASSWORD` in the host's
   secret settings and repeat step 3 against that database.

### Step 2 — purge from history (optional, destructive — needs your go-ahead)

Only worth doing after step 1, and only if the repository is or will become
public or shared. It rewrites every commit after `4651da7`, so all commit
hashes change.

Before starting:

- Merge or finish open branches; anything based on old history must be re-cloned.
- Make a full backup: `git clone --mirror <repo url> aanga-backup.git`.
- Tell anyone else with a clone that they will need to re-clone.

Procedure (using `git filter-repo`, the tool GitHub recommends):

```bash
pip install git-filter-repo

# A fresh clone - filter-repo refuses to run on a working repository.
git clone https://github.com/sounak9/AANGA-ECOMERCE-MAIN.git aanga-clean
cd aanga-clean

# replacements.txt: one line, the leaked value, then ==> and its replacement.
#   <leaked password>==>change-me-to-a-strong-password
git filter-repo --replace-text ../replacements.txt

# Check it is gone from every commit on every branch:
git log --all --oneline -S"<leaked password>"        # must print nothing

git remote add origin https://github.com/sounak9/AANGA-ECOMERCE-MAIN.git
git push --force --all
git push --force --tags
```

Then:

- Delete `replacements.txt` (it contains the password).
- Re-clone on every machine; do not pull into an old clone.
- GitHub keeps unreachable commits and cached views for a while. To have them
  removed immediately, contact GitHub Support and ask for the cached views and
  dangling commits of the repository to be purged.

**This step is not run automatically.** It is a force-push that rewrites shared
history; it needs an explicit decision.

## 2. Other items found during the hardening pass

- **Phone OTP has no SMS provider.** The code is generated and stored but never
  sent, so phone sign-in cannot work outside local development. It now uses a
  cryptographic random source and is no longer written to production logs.
  Either add a provider (MSG91 / Twilio — a paid service) or hide the option.
- **Razorpay webhook must be registered** in the Razorpay Dashboard once keys
  exist (Settings → Webhooks → `https://<api-host>/api/payments/webhook`,
  events `payment.captured`, `payment.failed`, `refund.processed`), with the
  same secret as `RAZORPAY_WEBHOOK_SECRET`.
- **`reconcile-payments` must be scheduled** — the webhook deliberately ignores
  captures younger than 15 minutes, so refunds of abandoned checkouts depend on
  this job. See `docs/DEPLOYMENT.md`.
- **Supabase service key** is a full-access credential. Keep it in the host's
  secret store only; rotate it in Supabase if it is ever pasted into chat,
  a ticket, or a commit.
- **30 product images are tracked in git** under `backend/static/uploads/`
  from before the folder was ignored. Harmless, but they will not exist on
  Render — production reads images from Supabase Storage.
