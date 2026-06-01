import { create } from "zustand";
import { v4 as uuid } from "uuid";
import { createDealAPI, fetchDealStatus } from "./rpc";

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
  arbitrationCountdown?: number;
  backendDealId?: string; // maps to the backend deal ID for polling
}

export interface CreateDealPayload {
  title: string;
  description: string;
  budget: number;
  deadline: string;
  criteria: string;
  chain: "arc" | "genlayer";
}

// ─── Store interface ──────────────────────────────────────────────────────────

interface DealStore {
  deals: Record<string, Deal>;
  isModalOpen: boolean;
  isPolling: boolean;

  openModal: () => void;
  closeModal: () => void;

  createDeal: (payload: CreateDealPayload) => Promise<Deal>;
  updateDealStatus: (id: string, status: DealStatus, event?: Omit<DealEvent, "id" | "timestamp">) => void;
  appendEvent: (id: string, event: Omit<DealEvent, "id" | "timestamp">) => void;
  raiseDispute: (id: string, reason?: string) => void;
  pollDealStatus: (id: string) => Promise<void>;
  stopPolling: () => void;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

// ─── Store ───────────────────────────────────────────────────────────────────

export const useDealStore = create<DealStore>((set, get) => ({
  deals: {},
  isModalOpen: false,
  isPolling: false,

  openModal: () => set({ isModalOpen: true }),
  closeModal: () => set({ isModalOpen: false }),

  createDeal: async (payload) => {
    // Create local deal entry immediately for UI responsiveness
    const localId = uuid();
    const deal: Deal = {
      id: localId,
      ...payload,
      status: "open",
      buyerAgent: "—",
      sellerAgent: "—",
      createdAt: Date.now(),
      updatedAt: Date.now(),
      events: [
        { id: uuid(), timestamp: Date.now(), message: "Creating deal via backend…", type: "info" },
      ],
    };
    set((s) => ({ deals: { ...s.deals, [deal.id]: deal }, isModalOpen: false }));

    try {
      // Call real backend to create the deal
      const result = await createDealAPI(payload);
      const backendDealId = result.deal_id;

      set((s) => {
        const d = s.deals[localId];
        if (!d) return s;
        return {
          deals: {
            ...s.deals,
            [localId]: {
              ...d,
              backendDealId,
              updatedAt: Date.now(),
              events: [
                ...d.events,
                { id: uuid(), timestamp: Date.now(), message: `Deal created on backend — ID: ${backendDealId}`, type: "success" },
              ],
            },
          },
        };
      });

      // Start polling for real status updates
      get().pollDealStatus(localId);
    } catch (err: any) {
      set((s) => {
        const d = s.deals[localId];
        if (!d) return s;
        return {
          deals: {
            ...s.deals,
            [localId]: {
              ...d,
              status: "open",
              updatedAt: Date.now(),
              events: [
                ...d.events,
                { id: uuid(), timestamp: Date.now(), message: `Failed to create deal: ${err.message}`, type: "error" },
              ],
            },
          },
        };
      });
    }

    return get().deals[localId];
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

  raiseDispute: (id, reason) => {
    const deal = get().deals[id];
    if (!deal?.backendDealId) return;

    // Update local state immediately
    set((s) => {
      const d = s.deals[id];
      if (!d) return s;
      return {
        deals: {
          ...s.deals,
          [id]: {
            ...d,
            status: "disputed",
            disputeReason: reason,
            updatedAt: Date.now(),
            events: [
              ...d.events,
              { id: uuid(), timestamp: Date.now(), message: `Dispute raised${reason ? `: ${reason}` : " by buyer agent"}`, type: "error" },
              { id: uuid(), timestamp: Date.now() + 50, message: "Lifecycle paused — awaiting GenLayer arbitration", type: "warning" },
            ],
          },
        },
      };
    });

    // Notify backend about the dispute (fire-and-forget, status will update via polling)
    const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
    if (API_BASE && deal.backendDealId) {
      fetch(`${API_BASE}/api/deals/${deal.backendDealId}/dispute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      }).catch(() => {}); // best-effort
    }
  },

  pollDealStatus: async (localId) => {
    set({ isPolling: true });
    let attempts = 0;
    const MAX_ATTEMPTS = 120; // ~4 minutes of polling at 2s intervals

    while (get().isPolling && attempts < MAX_ATTEMPTS) {
      const deal = get().deals[localId];
      if (!deal?.backendDealId) {
        await sleep(2000);
        attempts++;
        continue;
      }

      // Stop polling when deal reaches a terminal state
      if (["settled", "resolved", "disputed"].includes(deal.status)) {
        break;
      }

      try {
        const status = await fetchDealStatus(deal.backendDealId);
        
        set((s) => {
          const d = s.deals[localId];
          if (!d) return s;

          // Merge new events from backend
          const existingMsgSet = new Set(d.events.map((e) => e.message));
          const newEvents = (status.events || [])
            .filter((e: any) => !existingMsgSet.has(e.message))
            .map((e: any) => ({
              id: uuid(),
              timestamp: e.timestamp || Date.now(),
              message: e.message,
              type: (e.type || "info") as DealEvent["type"],
            }));

          return {
            deals: {
              ...s.deals,
              [localId]: {
                ...d,
                status: (status.status as DealStatus) || d.status,
                buyerAgent: status.buyerAgent || d.buyerAgent,
                sellerAgent: status.sellerAgent || d.sellerAgent,
                escrowTx: status.escrowTx || d.escrowTx,
                verificationScore: status.verificationScore ?? d.verificationScore,
                settlementTx: status.settlementTx || d.settlementTx,
                arbitrationOutcome: (status.arbitrationOutcome as ArbitrationOutcome) || d.arbitrationOutcome,
                updatedAt: Date.now(),
                events: [...d.events, ...newEvents],
              },
            },
          };
        });
      } catch {
        // Silently retry on network errors
      }

      await sleep(2000);
      attempts++;
    }

    set({ isPolling: false });
  },

  stopPolling: () => set({ isPolling: false }),
}));
