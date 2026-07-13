# LLMOps Gateway — Console

React + Tailwind ops dashboard for the LLMOps Gateway AI platform.

## Run locally

```bash
cd frontend
npm install
npm run dev      # http://localhost:3001
```

Runs in **demo mode** by default — `src/lib/demoData.js` generates a live-feeling
request stream so the UI is fully explorable without a backend running.

## Wire up to the real API

Swap the demo feed in `src/App.jsx` for real calls using `src/lib/api.js`
(already proxies `/api` to `http://localhost:8000` in `vite.config.js`):

```js
import { getAnalyticsSummary, getRequestHistory } from "./lib/api";
```

## Build

```bash
npm run build   # outputs to dist/
```
