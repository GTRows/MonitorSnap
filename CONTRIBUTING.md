# Contributing

## Requirements

- Windows 10/11
- Python 3.10+
- Node.js 20+

## Setup

```bash
git clone https://github.com/GTRows/MonitorSnap.git
cd MonitorSnap
dev.bat
```

Or manually:

```bash
cd electron-app
npm install
npm run electron:dev
```

The Electron main process spawns the Python backend automatically.

## Code Standards

- All code, comments, and identifiers in English
- Python: PEP 8, type hints on new functions, f-strings, max 100 chars/line
- TypeScript: strict mode, no `any` unless unavoidable
- React: functional components, Zustand for state
- CSS: TailwindCSS utility classes

## Project Layout

- `display_presets/` -- Python backend (Windows API, HTTP server, preset storage)
- `electron-app/electron/` -- Electron main process + preload
- `electron-app/src/` -- React renderer (pages, components, stores)

## Testing

Before submitting a PR:

- Test on a multi-monitor Windows setup
- Verify preset save/apply/delete works
- Check both dark and light themes
- Test the system tray menu
- Run `npx tsc --noEmit` for TypeScript errors

## Pull Requests

1. Fork the repo and clone it
2. Create your branch from `develop` (not `main`):
   ```bash
   git checkout develop
   git checkout -b feature/my-feature
   ```
3. Make your changes and commit
4. Push and open a PR targeting `develop`
5. After review, the maintainer merges into `develop`

Do not open PRs directly into `main`. Releases are cut from `develop` into `main` by the maintainer.
