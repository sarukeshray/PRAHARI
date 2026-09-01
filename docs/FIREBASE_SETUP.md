# Firebase setup

Everything in this file happens in a **browser**, in the Firebase Console — not
in the editor. It assumes no prior Firebase experience.

Budget about 25 minutes. You can do it while the backend work continues; nothing
here blocks anything else.

**What Firebase is used for, and only this:**

| Service | Used for |
|---|---|
| Authentication | Signing in the seven roles. Passwords never touch our database. |
| Storage | Completion photographs uploaded by Implementing Agencies, and lifecycle photographs from User Agencies. |
| Firestore | Not used. Skip any step that asks you to enable it. |

The application keeps all its own data in PostgreSQL/SQLite. Firebase holds
credentials and image files, nothing else.

---

## 1. Create the project

1. Go to **https://console.firebase.google.com**
2. Click **Create a project** (or "Add project")
3. Name it `prahari-demo`. Firebase will append a random suffix to make the
   project ID unique — something like `prahari-demo-4f21a`. **Write that full
   project ID down**, you need it twice later.
4. Google Analytics: **turn it off**. It adds a consent step you do not need.
5. Click **Create project**, wait for it to finish, then **Continue**.

---

## 2. Enable email/password sign-in

1. In the left sidebar choose **Build → Authentication**
2. Click **Get started**
3. On the **Sign-in method** tab, click **Email/Password**
4. Turn on the **first** toggle (Email/Password). Leave "Email link
   (passwordless sign-in)" **off**.
5. **Save**

### Create the demo accounts

Still in Authentication, open the **Users** tab and click **Add user** for each
row below. Use the same password for all of them so the demo is simple —
`Prahari@2026` works.

| Email | Role it maps to |
|---|---|
| `da.udaipur@prahari.demo` | District Authority |
| `da2.udaipur@prahari.demo` | District Authority (second reviewer, for reassignment) |
| `mp.udaipur@prahari.demo` | Member of Parliament |
| `diid@prahari.demo` | Ministry (MoSPI) |
| `sna.rajasthan@prahari.demo` | State Nodal Authority |
| `pwd.udaipur@prahari.demo` | Implementing Agency |
| `useragency.udaipur@prahari.demo` | User Agency |

These addresses are **not arbitrary** — they must match exactly. The seed script
already created matching rows in the `users` table keyed on these addresses, and
that table is what carries each account's role and the slice of data it may see.

After adding each user, Firebase shows a **User UID** column. You do not need to
copy these; the backend links accounts by email on first sign-in.

---

## 3. Enable Storage

1. Left sidebar → **Build → Storage**
2. Click **Get started**
3. Choose **Start in production mode** (we replace the rules in a moment)
4. Pick a location. **`asia-south1` (Mumbai)** is the right choice — it is the
   closest region and the natural answer if a juror asks where the data sits.
   **This cannot be changed later.**
5. Click **Done**

### Replace the security rules

Open the **Rules** tab in Storage, delete everything in the box, and paste this
in its place:

```
rules_version = '2';

service firebase.storage {
  match /b/{bucket}/o {

    // Photographs an implementing agency uploads against a work it is executing.
    // The path carries the work ID; the backend checks that the signed-in agency
    // is actually assigned to that work before it accepts the upload record.
    match /works/{workId}/progress/{fileName} {
      allow read: if request.auth != null;
      allow write: if request.auth != null
                   && request.resource.size < 10 * 1024 * 1024
                   && request.resource.contentType.matches('image/.*');
    }

    // Photographs a user agency uploads for an asset handed over to it.
    match /assets/{workId}/lifecycle/{fileName} {
      allow read: if request.auth != null;
      allow write: if request.auth != null
                   && request.resource.size < 10 * 1024 * 1024
                   && request.resource.contentType.matches('image/.*');
    }

    // Nothing else is writable, and nothing at all is public.
    match /{allPaths=**} {
      allow read, write: if false;
    }
  }
}
```

Click **Publish**.

**A note on what these rules can and cannot do.** Storage rules can check that
somebody is signed in and that the file is a reasonably sized image. They cannot
check that *this particular agency* is assigned to *this particular work* —
Firebase has no view of our database. That check happens in the backend, which
verifies assignment before recording the photograph and re-reads the file to
extract its EXIF. The rules are the outer fence; the real control is server-side.

---

## 4. Get the frontend config

1. Click the **gear icon** next to "Project Overview" → **Project settings**
2. Scroll to **Your apps** and click the **web icon** (`</>`)
3. App nickname: `prahari-web`. Do **not** tick "Also set up Firebase Hosting".
4. Click **Register app**
5. Firebase shows a `firebaseConfig` block. Copy the values.

Create **`frontend/.env.local`** — a new file, next to `package.json` — and fill
it in from that block:

```
VITE_FIREBASE_API_KEY=AIzaSy...
VITE_FIREBASE_AUTH_DOMAIN=prahari-demo-4f21a.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=prahari-demo-4f21a
VITE_FIREBASE_STORAGE_BUCKET=prahari-demo-4f21a.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789012
VITE_FIREBASE_APP_ID=1:123456789012:web:abc123def456
```

The `VITE_` prefix is required — Vite only exposes variables that start with it.

These values are **not secrets**. They identify your project to Firebase and are
visible in any browser that loads the app. What protects your data is the rules
above plus the backend's own checks, not the secrecy of this config.

`frontend/.env.local` is already covered by `.gitignore`.

---

## 5. Get the backend service account key

This one **is** a secret. It grants full administrative access to the project.

1. **Project settings → Service accounts** tab
2. Click **Generate new private key**, then **Generate key** on the warning
3. A `.json` file downloads, named something like
   `prahari-demo-4f21a-firebase-adminsdk-xxxxx.json`
4. Rename it to **`firebase_credentials.json`**
5. Move it to **`backend/app/config/firebase_credentials.json`**

Then add these lines to **`backend/.env`** (create it from `.env.example` if you
have not already):

```
FIREBASE_ENABLED=true
FIREBASE_CREDENTIALS_PATH=app/config/firebase_credentials.json
FIREBASE_STORAGE_BUCKET=prahari-demo-4f21a.firebasestorage.app
```

Use your real project ID in that bucket name.

> ### Do not commit this file
>
> `backend/app/config/firebase_credentials.json` is already listed in
> `.gitignore`, so git will ignore it. Verify with:
>
> ```powershell
> git status --short
> ```
>
> If `firebase_credentials.json` appears in that output, **stop** and tell me
> before committing. Anyone with this file can read and write everything in the
> project.
>
> If it ever does get committed, rotating the key is the fix: Service accounts →
> the key's row → delete, then generate a new one. Removing the file in a later
> commit is not enough, because it stays in the history.

---

## 6. Check it worked

Restart both servers so they pick up the new environment files, then:

```powershell
curl.exe http://127.0.0.1:8001/api/v1/health
```

Look for `"auth": "firebase"` in the response. If it says `"auth": "demo"`, the
backend did not find the credentials — check the path in `backend/.env` is
relative to the `backend/` directory, and that the file is really named
`firebase_credentials.json`.

Then open the app, pick **District Authority**, and sign in with
`da.udaipur@prahari.demo` / `Prahari@2026`.

---

## If you skip this

The application still runs. Without Firebase configured the backend falls back
to a **demo sign-in** that accepts the role you pick on the login screen without
a password, and photograph upload is disabled.

That fallback is fine for local development and it keeps the prototype
demonstrable, but it is **not** authentication — it trusts the client completely.
It refuses to start if the app is ever run with `ENV=production`, so it cannot
reach a deployment by accident.

---

## Troubleshooting

**"Firebase: Error (auth/invalid-api-key)"** — `frontend/.env.local` is missing,
misnamed, or Vite was not restarted. Vite reads env files only at startup.

**"auth/user-not-found" with a correct password** — the account exists in
Firebase but there is no matching row in our `users` table. Re-run the seed:
`python -m app.seed.generate --works 4000 --seed 42 --reset`.

**"Missing or insufficient permissions" on upload** — the Storage rules were not
published, or the file is over 10 MB.

**Health endpoint still says `"auth": "demo"`** — the backend could not read the
service account file. Check `backend/.env` and confirm the JSON file sits at
`backend/app/config/firebase_credentials.json`.
