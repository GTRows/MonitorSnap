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

1. Fork and create a feature branch
2. Make changes
3. Test thoroughly
4. Submit PR with clear description
