// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import { IAgenticCommerce } from "../BridgeReceiver.sol";

contract MockAgenticCommerce is IAgenticCommerce {
    
    enum JobStatus { Open, Funded, Submitted, Completed, Rejected, Expired }

    struct Job {
        uint256 id;
        address client;
        address provider;
        JobStatus status;
        bytes32 reason;
    }

    mapping(uint256 => Job) public jobs;
    uint256 public nextJobId = 1;

    event JobCreated(uint256 indexed jobId, address indexed client, address indexed provider);
    event JobRejected(uint256 indexed jobId, bytes32 reason);

    function createJob(address _provider) external returns (uint256) {
        uint256 jobId = nextJobId++;
        jobs[jobId] = Job({
            id: jobId,
            client: msg.sender,
            provider: _provider,
            status: JobStatus.Funded,
            reason: bytes32(0)
        });
        emit JobCreated(jobId, msg.sender, _provider);
        return jobId;
    }

    function reject(
        uint256 jobId,
        bytes32 reason,
        bytes calldata /*optParams*/
    ) external override {
        require(jobs[jobId].id != 0, "Job does not exist");
        jobs[jobId].status = JobStatus.Rejected;
        jobs[jobId].reason = reason;
        emit JobRejected(jobId, reason);
    }

    function getJobStatus(uint256 jobId) external view returns (uint8) {
        return uint8(jobs[jobId].status);
    }
}
