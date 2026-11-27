# KnowLegacy AI

Preserve practical knowledge from experienced automobile mechanics and make approved expertise available to junior mechanics.

## Project layout

- `backend/`: Python and FastAPI backend.
- `frontend/`: React and Vite frontend.
- `API_CONTRACT.md`: shared API specification, to be added during backend implementation.

The application has not been implemented yet.

## Collaboration

Use `main` for shared work. Develop the backend on `backend` and the frontend on `frontend`, then merge changes through pull requests.

```powershell
git switch backend
# Work in backend/, then commit your changes.
git add backend
git commit -m "Implement backend"
```

The frontend developer can create their branch from `main`:

```powershell
git switch main
git switch -c frontend
```

Agree on the shared API contract before integrating the applications. Keep API keys in local `.env` files and commit only `.env.example` files containing placeholders.
