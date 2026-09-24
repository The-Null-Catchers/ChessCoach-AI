# Android Release

ChessCoach AI builds production Android releases through the manual **Android Release AAB** GitHub Actions workflow.

The workflow does not use a debug signing key and does not fall back to unsigned release output.

## GitHub environment

Create a GitHub Environment named `production`.

Add this environment variable:

- `PRODUCTION_API_URL` — the HTTPS base API URL used by the mobile app, including `/api/v1` when appropriate.

Add these environment secrets:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

## Create an upload key

Keep the keystore outside the repository.

Example:

```bash
keytool -genkeypair -v \
  -keystore chesscoach-upload.jks \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias chesscoach-upload
```

Encode the file as a single-line base64 value before saving it in GitHub Secrets:

Linux:

```bash
base64 -w 0 chesscoach-upload.jks
```

macOS:

```bash
base64 < chesscoach-upload.jks | tr -d '\n'
```

Never commit the keystore, passwords, `key.properties`, or generated signing files.

## Build a release

In GitHub:

1. Open **Actions**.
2. Select **Android Release AAB**.
3. Choose **Run workflow**.
4. Use the `main` branch for store releases.

The workflow:

1. validates the production API URL and signing secrets,
2. generates the Android project from the committed Flutter source,
3. configures release signing without printing secret values,
4. runs Flutter analysis and tests,
5. builds a signed release AAB,
6. creates a SHA-256 checksum,
7. uploads the AAB and checksum as a GitHub Actions artifact.

The expected bundle path is:

```
mobile/build/app/outputs/bundle/release/app-release.aab
```

For Google Play, use Play App Signing and treat this keystore as the upload key. Keep an offline backup of the upload key in a secure location.
