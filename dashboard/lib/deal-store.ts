import { create } from "zustand";
import { v4 as uuid } from "uuid";

// ─── Types ────────────────────────────────────────────────────────────────────

export type DealStatus =
  | "open"
  | "negotiating"
  | "escrow_funded"
  | "executing"
  | "verifying"
  | "settled"
  | "disputed"
  | "arbitrating"
  | "resolved";

export type ArbitrationOutcome = "buyer_refund" | "seller_payout" | "split";

export interface DealEvent {
  id: string;
  timestamp: number;
  message: string;
  type: "info" | "success" | "warning" | "error" | "chain";
}

export interface Deal {
  id: string;
  title: string;
  description: string;
  budget: number;
  deadline: string;
  criteria: string;
  chain: "arc" | "genlayer";
  status: DealStatus;
  buyerAgent: string;
  sellerAgent: string;
  createdAt: number;
  updatedAt: number;
  events: DealEvent[];
  escrowTx?: string;
  verificationScore?: number;
  settlementTx?: string;
  disputeReason?: string;
  arbitrationOutcome?: ArbitrationOutcome;
  arbitrationCountdown?: number; // seconds remaining
}

export interface CreateDealPayload {
  title: string;
  description: string;
  budget: number;
  deadline: string;
  criteria: string;
  chain: "arc" | "genlayer";
}

// ─── Demo timeline ────────────────────────────────────────────────────────────

export const DEMO_STEPS: {
  status: DealStatus;
  event: Omit<DealEvent, "id" | "timestamp">;
}[] = [
  { status: "open",         event: { message: "Deal created and broadcast to agent network", type: "info" } },
  { status: "negotiating",  event: { message: "Agent 0x7a3f…c291 matched as provider — negotiating terms", type: "info" } },
  { status: "escrow_funded",event: { message: "Escrow funded on Arc Testnet — USDC locked in ConvenatContract", type: "chain" } },
  { status: "executing",    event: { message: "Execution started — provider agent processing task", type: "info" } },
  { status: "verifying",    event: { message: "Verification requested from GenLayer ConvenatContract", type: "chain" } },
  { status: "verifying",    event: { message: "GenLayer SLA check: criteria evaluated — score 97/100", type: "success" } },
  { status: "settled",      event: { message: "Settlement complete — USDC released to provider", type: "success" } },
];

// ─── Arbitration log sequences ────────────────────────────────────────────────

const ARBITRATION_LOGS: { delayMs: number; message: string; type: DealEvent["type"] }[] = [
  { delayMs: 0,    message: "GenLayer arbitration node selected — validator 0x9f2a…b341", type: "chain" },
  { delayMs: 1200, message: "Loading deal criteria and execution evidence…", type: "info" },
  { delayMs: 2400, message: "Evaluating buyer claim against on-chain execution proof", type: "info" },
  { delayMs: 3600, message: "Cross-referencing Arc Testnet escrow state", type: "chain" },
  { delayMs: 4800, message: "GenLayer consensus reached — preparing verdict", type: "warning" },
];

const OUTCOME_MESSAGES: Record<ArbitrationOutcome, { message: string; type: DealEvent["type"] }> = {
  buyer_refund:  { message: "Verdict: criteria not met — full refund issued to buyer agent", type: "success" },
  seller_payout: { message: "Verdict: criteria met — full payout released to seller agent", type: "success" },
  split:         { message: "Verdict: partial completion — 50/50 split settlement executed on Arc", type: "warning" },
};

// ─── Store interface ──────────────────────────────────────────────────────────

interface DealStore {
  deals: Record<string, Deal>;
  isModalOpen: boolean;
  isDemoRunning: boolean;
  isDemoMode: boolean; // dev/testing toggle

  openModal: () => void;
  closeModal: () => void;
  toggleDemoMode: () => void;

  createDeal: (payload: CreateDealPayload) => Deal;
  updateDealStatus: (id: string, status: DealStatus, event?: Omit<DealEvent, "id" | "timestamp">) => void;
  appendEvent: (id: string, event: Omit<DealEvent, "id" | "timestamp">) => void;
  raiseDispute: (id: string, reason?: string) => void;
  runDemo: (id: string) => Promise<void>;
  stopDemo: () => void;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function randomAgent() {
  const hex = () => Array.from({ length: 8 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
  return `0x${hex()}…${Array.from({ length: 4 }, () => Math.floor(Math.random() * 16).toString(16)).join("")}`;
}

function randomHash() {
  return `0x${Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join("")}`;
}

function pickOutcome(): ArbitrationOutcome {
  const roll = Math.random();
  if (roll < 0.4) return "buyer_refund";
  if (roll < 0.75) return "seller_payout";
  return "split";
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

// ─── Store ───────────────────────────────────────────────────────────────────

export const useDealStore = create<DealStore>((set, get) => ({
  deals: {},
  isModalOpen: false,
  isDemoRunning: false,
  isDemoMode: true, // on by default — judges can always trigger dispute

  openModal: () => set({ isModalOpen: true }),
  closeModal: () => set({ isModalOpen: false }),
  toggleDemoMode: () => set((s) => ({ isDemoMode: !s.isDemoMode })),

  createDeal: (payload) => {
    const deal: Deal = {
      id: uuid(),
      ...payload,
      status: "open",
      buyerAgent: randomAgent(),
      sellerAgent: "—",
      createdAt: Date.now(),
      updatedAt: Date.now(),
      events: [
        { id: uuid(), timestamp: Date.now(), message: "Deal created and broadcast to agent network", type: "info" },
      ],
    };
    set((s) => ({ deals: { ...s.deals, [deal.id]: deal }, isModalOpen: false }));
    return deal;
  },

  updateDealStatus: (id, status, event) => {
    set((s) => {
      const deal = s.deals[id];
      if (!deal) return s;
      return {
        deals: {
          ...s.deals,
          [id]: {
            ...deal,
            status,
            updatedAt: Date.now(),
            events: event
              ? [...deal.events, { id: uuid(), timestamp: Date.now(), ...event }]
              : deal.events,
          },
        },
      };
    });
  },

  appendEvent: (id, event) => {
    set((s) => {
      const deal = s.deals[id];
      if (!deal) return s;
      return {
        deals: {
          ...s.deals,
          [id]: {
            ...deal,
            updatedAt: Date.now(),
            events: [...deal.events, { id: uuid(), timestamp: Date.now(), ...event }],
          },
        },
      };
    });
  },

  raiseDispute: async (id, reason) => {
    // Stop any running demo first
    set((s) => {
      const deal = s.deals[id];
      if (!deal) return s;
      return {
        isDemoRunning: false,
        deals: {
          ...s.deals,
          [id]: {
            ...deal,
            status: "disputed",
            disputeReason: reason,
            updatedAt: Date.now(),
            events: [
              ...deal.events,
              { id: uuid(), timestamp: Date.now(), message: `Dispute raised${reason ? `: ${reason}` : " by buyer agent"}`, type: "error" },
              { id: uuid(), timestamp: Date.now() + 50, message: "Lifecycle paused — awaiting GenLayer arbitration", type: "warning" },
            ],
          },
        },
      };
    });

    await sleep(800);

    // Transition to arbitrating
    set((s) => {
      const deal = s.deals[id];
      if (!deal) return s;
      return {
        deals: {
          ...s.deals,
          [id]: {
            ...deal,
            status: "arbitrating",
            arbitrationCountdown: ARBITRATION_LOGS.length * 1.2 + 2,
            updatedAt: Date.now(),
            events: [
              ...deal.events,
              { id: uuid(), timestamp: Date.now(), message: "GenLayer arbitration initiated — validator nodes assembling", type: "chain" },
            ],
          },
        },
      };
    });

    // Stream arbitration logs
    for (const log of ARBITRATION_LOGS) {
      await sleep(log.delayMs === 0 ? 400 : 1200);
      set((s) => {
        const deal = s.deals[id];
        if (!deal || deal.status !== "arbitrating") return s;
        return {
          deals: {
            ...s.deals,
            [id]: {
              ...deal,
              updatedAt: Date.now(),
              events: [...deal.events, { id: uuid(), timestamp: Date.now(), message: log.message, type: log.type }],
            },
          },
        };
      });
    }

    await sleep(1400);

    // Pick outcome randomly
    const outcome = pickOutcome();
    const outcomeMsg = OUTCOME_MESSAGES[outcome];

    set((s) => {
      const deal = s.deals[id];
      if (!deal) return s;
      return {
        deals: {
          ...s.deals,
          [id]: {
            ...deal,
            status: "resolved",
            arbitrationOutcome: outcome,
            settlementTx: randomHash(),
            updatedAt: Date.now(),
            events: [
              ...deal.events,
              { id: uuid(), timestamp: Date.now(), message: "GenLayer consensus finalised — executing verdict on Arc Testnet", type: "chain" },
              { id: uuid(), timestamp: Date.now() + 50, ...outcomeMsg },
            ],
          },
        },
      };
    });
  },

  runDemo: async (id) => {
    set({ isDemoRunning: true });

    for (const step of DEMO_STEPS) {
      if (!get().isDemoRunning) break;

      await sleep(2000);

      // Check again after sleep (dispute may have been raised mid-demo)
      if (!get().isDemoRunning) break;
      const current = get().deals[id];
      if (!current || current.status === "disputed" || current.status === "arbitrating") break;

      set((s) => {
        const deal = s.deals[id];
        if (!deal) return s;

        const extraFields: Partial<Deal> = {};
        if (step.status === "escrow_funded") extraFields.escrowTx = randomHash();
        if (step.status === "verifying" && step.event.type === "success") extraFields.verificationScore = 97;
        if (step.status === "settled") {
          extraFields.settlementTx = randomHash();
          extraFields.sellerAgent = randomAgent();
        }

        return {
          deals: {
            ...s.deals,
            [id]: {
              ...deal,
              ...extraFields,
              status: step.status,
              updatedAt: Date.now(),
              events: [...deal.events, { id: uuid(), timestamp: Date.now(), ...step.event }],
            },
          },
        };
      });
    }

    set({ isDemoRunning: false });
  },

  stopDemo: () => set({ isDemoRunning: false }),
}));
