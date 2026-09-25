# End-to-end testing

ChessCoach AI runs full client workflows against a real FastAPI, PostgreSQL and Redis stack in GitHub Actions.

## Browser

The browser job starts the API and Next.js app, installs Chromium through Playwright, then validates a production-relevant path:

1. create an administrator account through the real registration endpoint;
2. land in the authenticated game library;
3. open the admin dashboard;
4. change a persisted feature flag;
5. reload and verify that the runtime flag state remains changed.

Run locally after starting PostgreSQL, Redis, the API and web app:

```bash
cd web
npm install
npx playwright install chromium
npm run e2e
```

## Android

The mobile job boots an Android emulator and runs the Flutter integration test against the real API on the host through `10.0.2.2`.

The integration test creates an account, verifies the authenticated shell, opens the Games tab, confirms the empty-library state, and signs out.

The CI-only generated Android manifest permits cleartext traffic because the test API is local HTTP. Production release networking remains unchanged and continues to require the production API configuration.

```bash
cd mobile
flutter test integration_test/auth_flow_test.dart -d <device> \
  --dart-define=API_URL=http://<reachable-host>:8000/api/v1
```
