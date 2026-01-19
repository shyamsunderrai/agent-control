# Agent Control UI

Next.js dashboard for managing Agent Control agents, controls, and policies. Runs on port 4000.

## Tech Stack

- **Next.js 15** (Pages Router) + **React 19** + **TypeScript**
- **Mantine 7** + **Jupiter DS** (Galileo's design system)
- **TanStack Query** for server state management
- **openapi-fetch** with auto-generated types from the server's OpenAPI spec

## Quick Start

```bash
pnpm install
pnpm dev              # starts on http://localhost:4000
```

To regenerate API types from a running server:

```bash
pnpm fetch-api-types  # fetches from http://localhost:8000/openapi.json
```

## Folder Structure

```
src/
├── pages/                 # Next.js routes
│   ├── _app.tsx           # App wrapper (providers, global styles)
│   ├── index.tsx          # Home page (agents list)
│   └── agents/[id].tsx    # Agent detail page
├── core/
│   ├── api/               # API client + auto-generated types
│   │   ├── client.ts      # openapi-fetch client with typed methods
│   │   ├── generated/     # Auto-generated from OpenAPI spec
│   │   └── types.ts       # Re-exported type aliases
│   ├── hooks/query-hooks/ # TanStack Query hooks (useAgent, useAgents, etc.)
│   ├── layouts/           # App shell with sidebar navigation
│   ├── page-components/   # Page-level components (home, agent-detail)
│   ├── providers/         # React context providers (QueryProvider)
│   └── types/             # Shared TypeScript types
├── components/            # Reusable UI components (icons, json-editor)
└── styles/                # Global CSS, fonts
```

## Key Patterns

- **API types are auto-generated** — run `pnpm fetch-api-types` after server API changes
- **Query hooks** wrap the `api` client and return typed data (see `core/hooks/query-hooks/`)
- **Page components** contain the actual UI logic; `pages/` files are thin wrappers that apply layouts
- **Evaluator forms** follow a registry pattern in `core/page-components/agent-detail/edit-control/evaluators/` — each evaluator type (json, sql, regex, etc.) has its own folder with `form.tsx`, `types.ts`, and `index.ts`
