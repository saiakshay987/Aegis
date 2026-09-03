# Aegis — Frontend

React + Vite + Tailwind frontend for the Financial Guardian system.

## Pages

| Route | Description |
|---|---|
| `/` | Landing page with system overview |
| `/login/customer` | Customer login (enter any `USR0001`–`USR0500`) |
| `/customer` | Dashboard · Oxygen gauge, balance, risk status |
| `/customer/projection` | 30/60/90-day cashflow chart |
| `/customer/repayment` | Adaptive repayment plans + consent flow |
| `/customer/anomalies` | ML-detected transaction anomalies |
| `/customer/buffer` | Survival buffer breakdown |
| `/login/admin` | Admin login (password: `aegis2024`) |
| `/admin` | Portfolio command center |
| `/admin/user/:id` | Per-user drilldown with radar + charts |

## Run

```bash
# 1. Start the backend first (from aegis/backend)
uvicorn main:app --reload --port 8000

# 2. Start the frontend (from aegis/frontend)
npm run dev
```

Open http://localhost:5173

The Vite dev server proxies all `/api` requests to `http://localhost:8000`.
