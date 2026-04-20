# Agent Control — MAS AIRG 2025 Compliance Demo

A fully executable local demo that deploys **5 financial AI agents** on Kubernetes and demonstrates how **Agent Control** enforces centralized AI governance across every agent interaction — mapping directly to the **Monetary Authority of Singapore's Guidelines on AI Risk Management (AIRG 2025)**.

---

## What This Demo Shows

The demo runs **19 scenarios** across 5 agents. Every scenario triggers a real policy evaluation through the Agent Control server — blocking harmful inputs, steering ambiguous outputs, and logging everything to an immutable audit trail — all enforced from a single control panel regardless of where agents are deployed.

| Agent | MAS AIRG Sections | Scenarios |
|---|---|---|
| Loan Underwriting | 4.3 Fairness, 4.4 Transparency, 4.8 Audit | 3 |
| Customer Support | 4.2 Data/PII, 4.7 Cybersecurity, 4.1 Governance | 4 |
| Trade Execution | 4.5 Human Oversight, 4.7 Cybersecurity, 4.3 Market Integrity | 4 |
| AML Compliance | 4.6 Monitoring, 4.5 Human Oversight, 4.8 Audit | 3 |
| Report Generation | 4.7 Cybersecurity, 4.2 Data Quality, 4.8 Change Management | 5 |

---

## Architecture

```
  ┌─────────────────────────────────────────────────────────────────┐
  │              Docker Desktop Kubernetes Cluster                   │
  │                                                                  │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │              Agent Control Server + UI                   │   │
  │  │         (Central Governance Control Panel)               │   │
  │  │  • Policy management    • Real-time audit events         │   │
  │  │  • Control templates    • Metrics & observability        │   │
  │  └──────────────────────┬──────────────────────────────────┘   │
  │                         │ evaluate_controls()                   │
  │     ┌───────────────────┼───────────────────┐                  │
  │     │                   │                   │                  │
  │  ┌──▼──┐  ┌──────┐  ┌──▼──┐  ┌─────┐  ┌──▼──┐              │
  │  │Loan │  │Cust  │  │Trade│  │ AML │  │Rpt  │              │
  │  │Underwt│ │Supprt│  │Exec │  │Comp │  │Gen  │              │
  │  └──┬──┘  └──┬───┘  └──┬──┘  └──┬──┘  └──┬──┘              │
  │     └────────┴──────────┴────────┴─────────┘                  │
  │                         │ Ollama API                            │
  │                  ┌──────▼──────┐                               │
  │                  │   Ollama    │                               │
  │                  │ llama3.2:3b │                               │
  │                  └─────────────┘                               │
  └─────────────────────────────────────────────────────────────────┘
```

**Components:**

| Component | Image / Source | Port (host) | Purpose |
|---|---|---|---|
| Agent Control Server | `galileoai/agent-control-server:latest` | 30800 | Policy engine, evaluation API, audit log |
| Agent Control UI | `galileoai/agent-control-ui:latest` | 30400 | Control panel — manage policies, view events |
| PostgreSQL | `postgres:15` | — (internal) | Persistent store for policies, controls, audit events |
| Ollama | `ollama/ollama:latest` | 31434 | Local LLM inference (llama3.2:3b) |
| Demo Agents (×5) | `agent-control-demo-agents:latest` | 30081–30085 | Financial AI agents calling Agent Control SDK |

---

## Prerequisites

- **Docker Desktop** with Kubernetes enabled (Settings → Kubernetes → Enable Kubernetes)
- **kubectl** configured to use the `docker-desktop` context
- **Python 3.12+**
- At least **8 GB RAM** available to Docker (Ollama + agents + server)
- At least **5 GB free disk** (Ollama model is ~2 GB)

Verify your cluster is ready:

```bash
kubectl config use-context docker-desktop
kubectl get nodes
# Should show: docker-desktop   Ready
```

---

## Setup — Step by Step

### Step 1 — Build the SDK wheels

```bash
python3 scripts/build.py evaluators
python3 scripts/build.py sdk
```

**What this does:** The Agent Control SDK bundles its internal packages (models, engine, telemetry) at wheel build time. `build.py evaluators` compiles the built-in evaluators (regex, list, json, sql) into a wheel. `build.py sdk` copies those packages into the SDK source tree and builds the final SDK wheel. Both wheels are needed before the Docker image can be built.

```bash
# Copy the built wheels to the agents folder
cp dist/*.whl demo/agents/dist/
```

**What this does:** Places the freshly-built SDK wheels where the agents' Dockerfile can find them. The Dockerfile installs these wheels before installing any other agent dependencies, ensuring the exact local version is used.

---

### Step 2 — Pull the server images (Apple Silicon)

```bash
docker pull --platform linux/amd64 galileoai/agent-control-server:latest
docker pull --platform linux/amd64 galileoai/agent-control-ui:latest
```

**What this does:** The Galileo images are published for `linux/amd64` only. On Apple Silicon (M1/M2/M3) Macs, Docker Desktop runs amd64 containers via Rosetta 2 translation. Pulling explicitly with `--platform linux/amd64` forces Docker to cache the correct manifest. Without this flag, Docker may attempt to pull an arm64 manifest that does not exist and fail with "no matching manifest for linux/arm64/v8".

---

### Step 3 — Build the demo agents image

```bash
docker build --platform linux/amd64 \
  -f demo/agents/Dockerfile \
  -t agent-control-demo-agents:latest \
  .
```

**What this does:** Builds a single Docker image that contains all 5 demo agents. The `AGENT_TYPE` environment variable (set per-pod in Kubernetes) determines which agent each container runs. The build context is the repository root so the Dockerfile can access both the SDK wheels and the agent source files. The `--platform linux/amd64` flag is required for consistency with the server images on Apple Silicon.

---

### Step 4 — Create the Kubernetes namespace

```bash
kubectl apply -f demo/k8s/00-namespace.yaml
```

**What this does:** Creates the `agent-control-demo` namespace that isolates all demo resources from other workloads on your cluster. All subsequent manifests deploy into this namespace. Running `kubectl delete namespace agent-control-demo` during teardown removes everything cleanly.

---

### Step 5 — Deploy PostgreSQL

```bash
kubectl apply -f demo/k8s/01-postgres.yaml
```

**What this does:** Deploys a PostgreSQL 15 pod with a `PersistentVolumeClaim` so the database survives pod restarts. The Agent Control Server uses this database to store agent registrations, policies, controls, and the complete audit event history. The connection string `postgresql+psycopg://agent_control:agent_control@postgres:5432/agent_control` is passed to the server via environment variable.

Wait for it to be ready before proceeding:

```bash
kubectl wait --for=condition=ready pod -l app=postgres -n agent-control-demo --timeout=60s
```

---

### Step 6 — Deploy Agent Control Server and UI

```bash
kubectl apply -f demo/k8s/02-agent-control.yaml
```

**What this does:** Deploys two pods:
- **Agent Control Server** (`galileoai/agent-control-server:latest`) — the policy evaluation engine. Agents call its `/api/v1/evaluate` endpoint before and after every LLM call or tool invocation. The server looks up the agent's assigned policy, runs all matching controls against the input/output, and returns a decision (`pass`, `deny`, `steer`, or `observe`).
- **Agent Control UI** (`galileoai/agent-control-ui:latest`) — a Next.js control panel. From here you can create and edit policies, enable/disable controls, browse the real-time audit event log, and see all registered agents.

Both services are exposed as `NodePort` so they are accessible from `localhost` on your Mac.

Wait for both to be ready:

```bash
kubectl wait --for=condition=ready pod -l app=agent-control-server -n agent-control-demo --timeout=120s
kubectl wait --for=condition=ready pod -l app=agent-control-ui -n agent-control-demo --timeout=120s
```

Verify the server is healthy:

```bash
curl http://localhost:30800/health
# Expected: {"status":"healthy","version":"7.4.1"}
```

---

### Step 7 — Deploy Ollama

```bash
kubectl apply -f demo/k8s/03-ollama.yaml
```

**What this does:** Deploys Ollama as a pod inside the cluster. An `initContainer` runs `ollama pull llama3.2:3b` before the main container starts — this downloads the ~2 GB model on first run and takes several minutes. All 5 demo agents share this single Ollama endpoint at `http://ollama:11434`, keeping the resource footprint low.

Monitor the model download (this is the slowest step):

```bash
kubectl logs -n agent-control-demo deployment/ollama -f
# Wait until you see: "success" for the pull
```

The demo runner will use mock LLM responses if Ollama is not yet ready, so you can proceed to the next step in parallel.

---

### Step 8 — Deploy the 5 demo agents

```bash
kubectl apply -f demo/k8s/04-agents.yaml
```

**What this does:** Deploys 5 separate pods from the single `agent-control-demo-agents:latest` image, each with a different `AGENT_TYPE` environment variable (`loan_underwriting`, `customer_support`, `trade_execution`, `aml_compliance`, `report_generation`). Each pod runs a FastAPI server that:
1. On startup, calls `agent_control.init()` which registers the agent with the Agent Control Server and fetches its assigned controls.
2. Exposes `GET /health` and `POST /scenarios/run`.
3. Periodically refreshes its policy from the server (every 30 seconds).

Wait for all agents to be ready:

```bash
kubectl wait --for=condition=ready pod -l app=loan-underwriting-agent -n agent-control-demo --timeout=60s
kubectl wait --for=condition=ready pod -l app=customer-support-agent -n agent-control-demo --timeout=60s
kubectl wait --for=condition=ready pod -l app=trade-execution-agent -n agent-control-demo --timeout=60s
kubectl wait --for=condition=ready pod -l app=aml-compliance-agent -n agent-control-demo --timeout=60s
kubectl wait --for=condition=ready pod -l app=report-generation-agent -n agent-control-demo --timeout=60s
```

Verify all agent health endpoints:

```bash
for port in 30081 30082 30083 30084 30085; do
  echo -n "Port $port: "; curl -s http://localhost:$port/health
  echo
done
```

---

### Step 9 — Install the Python SDK locally

```bash
python3 -m venv demo/.venv
demo/.venv/bin/pip install \
    demo/agents/dist/agent_control_evaluators-*.whl \
    demo/agents/dist/agent_control_sdk-*.whl \
    httpx rich
```

**What this does:** Creates a local Python virtual environment for running the policy setup script and demo runner from your Mac (outside the cluster). The SDK wheels are installed so the local Python process can communicate with the Agent Control Server using the same SDK the agents use inside Kubernetes.

---

### Step 10 — Create policies and assign controls

```bash
demo/.venv/bin/python demo/policies/setup_policies.py --server http://localhost:30800
```

**What this does:** Calls the Agent Control API to create 5 policies (one per agent), create 17 governance controls, add each control to its policy, and assign each policy to its agent. After this step, every agent call to `evaluate_controls()` will be evaluated against its assigned controls. The script is idempotent — if an agent already has policies assigned it is skipped, so you can safely re-run it.

Verify all agents have policies assigned:

```bash
curl -s http://localhost:30800/api/v1/agents | python3 -m json.tool
# Each agent should show "active_controls_count" > 0
```

---

### Step 11 — Run the demo

```bash
demo/.venv/bin/python demo/demo_runner.py \
  --server http://localhost:30800 \
  --ollama http://localhost:31434
```

**What this does:** Runs all 19 compliance scenarios sequentially across the 5 agents. For each scenario it calls `evaluate_controls()` (pre or post LLM/tool evaluation), prints the control decision with rich formatting, and displays a final MAS AIRG 2025 coverage table. All interactions are logged in real time to the Agent Control Server's audit trail, which you can browse in the UI at `http://localhost:30400`.

---

### Access URLs

| Service | URL | Notes |
|---|---|---|
| Agent Control UI | http://localhost:30400 | Control panel — agents, policies, audit events |
| Agent Control API | http://localhost:30800 | REST API for programmatic access |
| Ollama API | http://localhost:31434 | Local LLM inference endpoint |
| Loan Underwriting Agent | http://localhost:30081 | POST /scenarios/run |
| Customer Support Agent | http://localhost:30082 | POST /scenarios/run |
| Trade Execution Agent | http://localhost:30083 | POST /scenarios/run |
| AML Compliance Agent | http://localhost:30084 | POST /scenarios/run |
| Report Generation Agent | http://localhost:30085 | POST /scenarios/run |

---

## Teardown

```bash
kubectl delete namespace agent-control-demo
docker rmi agent-control-demo-agents:latest
```

**What this does:** Deletes the namespace and every resource inside it (pods, services, PVCs, ConfigMaps). The second command removes the locally-built agents image. The Galileo server and UI images remain cached in Docker for faster re-deployment.

---

## MAS AIRG 2025 — Controls Implemented

The MAS Guidelines on AI Risk Management (November 2025) define 8 risk management areas for financial institutions deploying AI. This demo maps Agent Control policies to each area.

---

### Section 4.1 — Oversight and Governance

**Requirement:** Financial institutions must maintain a centralised AI inventory and ensure appropriate human accountability for AI decisions.

**How Agent Control addresses it:** Agent Control acts as the central AI inventory. Every agent self-registers on startup with its name, description, version, and step schemas. All agents — regardless of framework, language, or deployment location — are visible in a single control panel. Policies can be updated centrally and take effect across all agents within 60 seconds via the background policy refresh loop.

---

### Section 4.2 — Data Management and Privacy

**Requirement:** AI systems must prevent leakage of personal data and ensure outputs do not expose sensitive customer information.

**Policy: `customer-support-policy`**

| Control | Type | Rule |
|---|---|---|
| `customer-privacy-block-pii-output` | DENY (post-eval) | Blocks any LLM response containing Singapore NRIC numbers (`[STFG]\d{7}[A-Z]`) or credit card numbers (16-digit patterns) |

**Policy: `report-generation-policy`**

| Control | Type | Rule |
|---|---|---|
| `report-security-block-credential-exposure` | DENY (post-eval) | Blocks reports containing database connection strings, API keys (`sk-`, `api_key=`), or passwords in plaintext |

**Demo scenario — PII Leakage Block:**
The agent constructs a response containing a customer's NRIC and credit card number. The post-evaluation control detects the patterns and returns `deny` before the response is sent to the user.

---

### Section 4.3 — Fairness and Bias

**Requirement:** AI models used in credit, insurance, and other decisions must not discriminate on protected characteristics such as age, gender, race, or religion.

**Policy: `loan-underwriting-policy`**

| Control | Type | Rule |
|---|---|---|
| `loan-fairness-block-protected-attributes` | DENY (pre-eval) | Blocks any prompt that references protected attributes (`age`, `gender`, `race`, `ethnicity`, `religion`, `marital status`, `national origin`, `disability`, `sexual orientation`) in combination with decision language (`factor`, `consider`, `weight`, `use as`) |

**Policy: `trade-execution-policy`**

| Control | Type | Rule |
|---|---|---|
| `trade-integrity-block-insider-language` | DENY (post-eval) | Blocks trade recommendations referencing insider information, non-public material, or confidential sources |

**Demo scenario — Discriminatory Attribute Block:**
A prompt instructs the loan agent to consider the applicant's age and gender as risk factors. The pre-evaluation control matches the pattern and returns `deny` before the LLM is ever called, preventing biased reasoning from entering the model context.

---

### Section 4.4 — Transparency and Explainability

**Requirement:** AI systems making consequential decisions must provide human-understandable explanations for those decisions.

**Policy: `loan-underwriting-policy`**

| Control | Type | Rule |
|---|---|---|
| `loan-transparency-require-explanation` | STEER (post-eval) | Detects loan decisions (approve/deny) that do not contain reasoning language (`reason`, `because`, `based on`, `criteria`). Returns steering guidance requiring the agent to regenerate with a full explanation. |

**Demo scenario — Missing Explanation Steer:**
The LLM returns "DENIED." with no justification. The post-evaluation control detects the missing explanation and returns `steer` with a message: "Regenerate with criteria-based reasoning including debt-to-income ratio, credit history, and collateral assessment." The agent receives this guidance and retries.

---

### Section 4.5 — Human Oversight and Control

**Requirement:** High-risk or high-impact AI actions must include a mandatory human review step before execution.

**Policy: `trade-execution-policy`**

| Control | Type | Rule |
|---|---|---|
| `trade-human-oversight-large-amount` | STEER (pre-eval) | Checks the `amount` field in the tool input JSON. If `amount >= 1,000,000`, pauses execution and requires a compliance officer to provide written approval before the trade proceeds. |

**Policy: `aml-compliance-policy`**

| Control | Type | Rule |
|---|---|---|
| `aml-escalate-low-confidence` | STEER (post-eval) | Detects uncertainty language in AML screening outputs (`possibly`, `not sure`, `might be`, `uncertain`, `unclear`). Redirects to senior analyst review rather than allowing auto-clearance. |

**Demo scenario — Large Trade Human Oversight:**
A $5M buy order triggers the control. The agent receives `steer` with the message: "Trade value exceeds $1M oversight threshold. Submit trade details to compliance officer for approval, record the approval reference number, and only execute after receiving explicit written approval."

---

### Section 4.6 — Monitoring

**Requirement:** Financial institutions must implement continuous monitoring of AI system behaviour including AML/CTF transaction screening.

**Policy: `aml-compliance-policy`**

| Control | Type | Rule |
|---|---|---|
| `aml-block-sanctioned-entity-clearance` | DENY (post-eval) | If the output contains clearance language (`clear`, `approve`, `false positive`) AND the input mentions OFAC or sanctioned entities, the auto-clearance is blocked. Sanctioned entity matches must go to a human reviewer. |
| `aml-audit-all-screening-decisions` | OBSERVE (post-eval) | Every AML screening output is logged to the audit trail regardless of decision outcome. Provides the complete monitoring record required by MAS for AML/CTF compliance. |

**Demo scenario — Sanctioned Entity Clearance Block:**
The LLM confidently clears a transaction as a false positive despite the input flagging an OFAC SDN list match. The control detects both the clearance language and the OFAC reference and returns `deny`, forcing human escalation.

---

### Section 4.7 — Cybersecurity

**Requirement:** AI systems must be protected against adversarial attacks including prompt injection, SQL injection, and code execution exploits.

**Policy: `customer-support-policy`**

| Control | Type | Rule |
|---|---|---|
| `customer-security-block-prompt-injection` | DENY (pre-eval) | Blocks inputs containing instruction-override patterns (`ignore previous instructions`, `you are now`, `disregard your`, `new persona`, `override your`) |
| `customer-access-control-sensitive-ops` | STEER (pre-eval) | Detects fund transfer or account modification requests that lack an explicit authentication step, requiring the agent to confirm identity before proceeding |

**Policy: `trade-execution-policy`**

| Control | Type | Rule |
|---|---|---|
| `trade-security-block-sql-injection` | DENY (pre-eval) | Blocks market data queries containing destructive SQL operations (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `TRUNCATE`, `UNION`, `EXEC`) |

**Policy: `report-generation-policy`**

| Control | Type | Rule |
|---|---|---|
| `report-security-block-dangerous-code` | DENY (post-eval) | Blocks generated code containing system-level calls (`os.system`, `subprocess`, `shutil.rmtree`, `eval(`, `exec(`) |
| `report-security-block-destructive-sql` | DENY (post-eval) | Blocks generated SQL containing destructive operations (`TRUNCATE`, `DROP TABLE`, `DELETE FROM`) |

**Demo scenario — SQL Injection Block:**
An attacker queries market data with `SELECT * FROM trades; DROP TABLE trades;--`. The pre-evaluation control matches `DROP` and returns `deny` before the query reaches the database.

---

### Section 4.8 — Audit Trail and Change Management

**Requirement:** All AI decisions and system changes must be recorded in an immutable audit log for regulatory review.

**Policy: `loan-underwriting-policy`**

| Control | Type | Rule |
|---|---|---|
| `loan-audit-all-decisions` | OBSERVE (post-eval) | Every loan decision output is logged to the audit trail, capturing the full input context, LLM output, and timestamp. |

**Policy: `trade-execution-policy`**

| Control | Type | Rule |
|---|---|---|
| `trade-audit-all-recommendations` | OBSERVE (post-eval) | Any output containing trade action language (`buy`, `sell`, `hold`, `execute`, `recommend`) is logged to the audit trail. |

**Policy: `aml-compliance-policy`**

| Control | Type | Rule |
|---|---|---|
| `aml-audit-all-screening-decisions` | OBSERVE (post-eval) | Every AML screening decision is logged regardless of outcome. |

**Policy: `report-generation-policy`**

| Control | Type | Rule |
|---|---|---|
| `report-quality-flag-placeholder-data` | STEER (post-eval) | Detects reports containing unresolved placeholder tokens (`[TODO`, `[PLACEHOLDER`, `TBD`, `INSERT VALUE HERE`). Steers the agent to resolve all placeholders before submission, preventing incomplete data from entering regulatory filings. |

All `observe` events are visible in real time at `http://localhost:30400` under the Audit Events section.

---

## Agent Control as Centralized Governance

One of the core design principles of Agent Control is that governance is **decoupled from the agent**. The agent code calls `evaluate_controls()` — it does not contain the policy logic. Policies live in the Agent Control Server and are applied uniformly regardless of:

### Framework Independence

Agents can be built with any framework — LangChain, LlamaIndex, AutoGen, CrewAI, Strands, or plain Python. The Agent Control SDK is a lightweight wrapper that evaluates inputs and outputs at runtime. The 5 demo agents are plain Python with httpx for Ollama calls, but the same SDK and the same server govern a LangChain agent, a Strands agent, or a custom framework equally.

```
LangChain agent   ─┐
LlamaIndex agent  ─┤
AutoGen agent     ─┼──► Agent Control Server (single policy store)
CrewAI agent      ─┤         ↑
Plain Python agent─┘    Same policies, same audit log
```

### Deployment Location Independence

The Agent Control Server is a single network endpoint. Agents connect to it via `AGENT_CONTROL_URL`. This can be:

| Deployment | AGENT_CONTROL_URL example | How it works |
|---|---|---|
| Local Kubernetes (this demo) | `http://agent-control:8000` | In-cluster DNS resolves the service |
| Cloud (AWS EKS) | `https://agent-control.internal.mybank.com` | Private DNS inside VPC |
| Cloud (Azure AKS) | `https://agent-control.mybank.azure.com` | Internal load balancer |
| On-premise (VM) | `http://10.10.5.20:8000` | Direct IP or internal DNS |
| Hybrid (agent on-prem, server in cloud) | `https://agent-control.mybank.com` | TLS + API key auth |

An agent deployed on-premise can be governed by a policy server in a private cloud. An agent running in AWS can be governed by the same policy server as an agent running on-premise in Singapore. The governance boundary is the network connection, not the deployment boundary.

### Real-Time Policy Updates

Policies updated in the UI or via the API take effect within **30–60 seconds** across every connected agent via the background policy refresh loop. There is no agent restart, no redeployment, and no code change required. A compliance officer can:
- Tighten a fairness control after a regulatory review
- Temporarily disable a control for a maintenance window
- Add a new data protection rule in response to a new MAS circular

All changes are reflected live across every agent that holds the affected policy.

### The Control Panel as AI Inventory

The Agent Control UI at `http://localhost:30400` serves as the **AI Inventory** required by MAS 4.1. It shows:
- All registered agents with their version, description, and registration timestamp
- All controls assigned to each agent, with their evaluator type, scope (pre/post, LLM/tool), and current enabled/disabled state
- All policies and which agents they are assigned to
- A real-time audit event log showing every evaluate call, the input/output (redacted if configured), the control that fired, and the decision taken

This gives a compliance officer or auditor a single pane of glass across the entire AI estate.

---

## Repository Structure

```
agent-control/
├── README.md                         ← This file
├── scripts/
│   └── build.py                      ← Builds SDK + evaluator wheels
├── demo/
│   ├── demo_runner.py                ← Rich terminal demo runner (19 scenarios)
│   ├── agents/
│   │   ├── Dockerfile                ← Single image for all 5 agents
│   │   ├── requirements.txt          ← Agent Python dependencies
│   │   ├── main.py                   ← FastAPI entrypoint, lifespan init
│   │   ├── common.py                 ← Shared ScenarioResult, Ollama client
│   │   ├── loan_underwriting.py      ← 3 MAS 4.3/4.4/4.8 scenarios
│   │   ├── customer_support.py       ← 4 MAS 4.2/4.7/4.1 scenarios
│   │   ├── trade_execution.py        ← 4 MAS 4.5/4.7/4.3 scenarios
│   │   ├── aml_compliance.py         ← 3 MAS 4.6/4.5/4.8 scenarios
│   │   ├── report_generation.py      ← 5 MAS 4.7/4.2/4.8 scenarios
│   │   └── dist/                     ← Pre-built SDK wheels (populated by build.py)
│   ├── k8s/
│   │   ├── 00-namespace.yaml         ← agent-control-demo namespace
│   │   ├── 01-postgres.yaml          ← PostgreSQL with PVC
│   │   ├── 02-agent-control.yaml     ← Server (NodePort 30800) + UI (NodePort 30400)
│   │   ├── 03-ollama.yaml            ← Ollama with llama3.2:3b pull initContainer
│   │   └── 04-agents.yaml            ← 5 agent deployments (NodePorts 30081–30085)
│   └── policies/
│       └── setup_policies.py         ← Creates 5 policies, 17 controls, assigns to agents
├── sdks/
│   └── python/                       ← Agent Control Python SDK source
└── evaluators/
    └── builtin/                      ← Built-in evaluators (regex, list, json, sql)
```

---

## Troubleshooting

**Agent pods are Running but not registered in the server**

The agents register with the server during pod startup via `agent_control.init()`. If the server was not ready (failing readiness probe) when the agents started, registration fails silently and is not retried by the policy refresh loop. Fix: restart the agent deployments after the server is confirmed healthy.

```bash
kubectl rollout restart deployment -n agent-control-demo \
  loan-underwriting-agent customer-support-agent \
  trade-execution-agent aml-compliance-agent report-generation-agent
```

**ImagePullBackOff on galileoai images**

The Galileo images are `linux/amd64` only. On Apple Silicon, you must pre-pull them before Kubernetes can use them:

```bash
docker pull --platform linux/amd64 galileoai/agent-control-server:latest
docker pull --platform linux/amd64 galileoai/agent-control-ui:latest
```

Also ensure `imagePullPolicy: IfNotPresent` is set in `demo/k8s/02-agent-control.yaml` (not `Always`), so Kubernetes uses the locally cached image.

**Ollama pod stuck in Init:0/1**

The init container is downloading the llama3.2:3b model (~2 GB). This is normal on first run. Monitor progress:

```bash
kubectl logs -n agent-control-demo deployment/ollama -c model-puller -f
```

The demo runner works without Ollama — it falls back to mock LLM responses automatically.

**setup_policies.py: 409 Conflict on policy creation**

This happens when the script previously failed after creating a policy but before assigning it to an agent. The script now handles this automatically by scanning for the orphaned policy ID and continuing setup. Just re-run the script.

**UI not loading at localhost:30400**

Verify the UI pod is ready and the service is bound:

```bash
kubectl get pods -n agent-control-demo -l app=agent-control-ui
kubectl get svc -n agent-control-demo agent-control-ui
curl -I http://localhost:30400
```
