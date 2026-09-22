# Development

Start the full local stack with `docker compose up --build`.

Backend tests: `cd backend && pytest`  
Backend lint: `cd backend && ruff check app tests`  
Web: `cd web && npm install && npm run build`  
Flutter: `cd mobile && flutter pub get && flutter analyze`
