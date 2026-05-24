import { type Hex, erc20Abi, parseUnits } from "viem";
import { useAccount, useWalletClient, usePublicClient } from "wagmi";
import { useState } from "react";
import { ARC_CONVENAT_ABI, USDC_ABI, CONTRACT_ADDRESSES } from "@/lib/abi";
import { useDealStore } from "@/lib/deal-store";

const USDC_DECIMALS = 6; // USDC on Arc has 6 decimals

export function useCreateDeal() {
  const { address, isConnected } = useAccount();
  const { data: walletClient } = useWalletClient();
  const publicClient = usePublicClient();
  const { createDeal } = useDealStore();
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createOnChainDeal = async (params: {
    provider: `0x${string}`;
    description: string;
    budgetUsdc: number; // in USDC dollars
    deadlineDays?: number;
  }) => {
    if (!isConnected || !address || !walletClient || !publicClient) {
      setError("Connect your wallet first");
      return null;
    }

    setIsCreating(true);
    setError(null);

    try {
      const { provider, description, budgetUsdc, deadlineDays = 7 } = params;
      const budgetWei = parseUnits(budgetUsdc.toFixed(6), USDC_DECIMALS);
      const expiredAt = BigInt(Math.floor(Date.now() / 1000) + deadlineDays * 86400);
      const zeroAddr = "0x0000000000000000000000000000000000000000" as Hex;

      // Step 1: Approve USDC spending by the contract
      console.log("Approving USDC...");
      const approveHash = await walletClient.writeContract({
        address: CONTRACT_ADDRESSES.usdc,
        abi: USDC_ABI,
        functionName: "approve",
        args: [CONTRACT_ADDRESSES.arc, budgetWei],
      });
      console.log("Approve tx:", approveHash);

      // Wait for approval to confirm
      const approveReceipt = await publicClient.waitForTransactionReceipt({ hash: approveHash });
      if (approveReceipt.status !== "success") throw new Error("USDC approval failed");

      // Step 2: Create the job on-chain
      console.log("Creating job...");
      const createHash = await walletClient.writeContract({
        address: CONTRACT_ADDRESSES.arc,
        abi: ARC_CONVENAT_ABI,
        functionName: "createJob",
        args: [provider, address, expiredAt, description, zeroAddr],
      });
      console.log("createJob tx:", createHash);
      const createReceipt = await publicClient.waitForTransactionReceipt({ hash: createHash });

      // Extract job ID from event logs
      const jobCreatedLog = createReceipt.logs.find(
        (log) => log.address.toLowerCase() === CONTRACT_ADDRESSES.arc.toLowerCase()
      );
      const jobId = jobCreatedLog ? Number(jobCreatedLog.topics[1]) : 0;

      // Step 3: Fund the job escrow
      console.log("Funding escrow...");
      const fundHash = await walletClient.writeContract({
        address: CONTRACT_ADDRESSES.arc,
        abi: ARC_CONVENAT_ABI,
        functionName: "fund",
        args: [BigInt(jobId), "0x" as Hex],
      });
      console.log("fund tx:", fundHash);
      await publicClient.waitForTransactionReceipt({ hash: fundHash });

      // Create local deal record
      const deal = createDeal({
        title: description,
        description,
        budget: budgetUsdc,
        deadline: new Date(Date.now() + deadlineDays * 86400000).toISOString(),
        criteria: "",
        chain: "arc",
      });

      return {
        dealId: deal.id,
        jobId,
        approveTx: approveHash,
        createTx: createHash,
        fundTx: fundHash,
      };
    } catch (err: any) {
      console.error("Deal creation failed:", err);
      setError(err?.message || "Transaction failed");
      return null;
    } finally {
      setIsCreating(false);
    }
  };

  return { createOnChainDeal, isCreating, error };
}
