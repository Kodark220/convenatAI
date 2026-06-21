// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ConvenatCommerce
 * @notice Full ERC-8183 contract for convenatAI agent commerce.
 * Handles the full job lifecycle: create → setBudget → fund → submit → complete/reject.
 * Backend uses Circle API for USDC escrow; this contract tracks job state on-chain.
 * 
 * Deployed on: Arc Testnet
 * Owner: convenatAI deployer
 */
contract ConvenatCommerce {

    enum JobStatus { Open, Funded, Submitted, Completed, Rejected, Expired }

    struct Job {
        uint256 id;
        address client;
        address provider;
        address evaluator;
        uint256 expiredAt;
        string description;
        address hook;
        JobStatus status;
        bytes32 reason;
        uint256 budget;
    }

    address public owner;
    uint256 public nextJobId = 1;
    mapping(uint256 => Job) public jobs;

    event JobCreated(uint256 indexed jobId, address indexed client, address indexed provider);
    event BudgetSet(uint256 indexed jobId, uint256 amount);
    event JobFunded(uint256 indexed jobId);
    event Submitted(uint256 indexed jobId, bytes32 deliverable);
    event Completed(uint256 indexed jobId, bytes32 reason);
    event JobRejected(uint256 indexed jobId, bytes32 reason);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Create a new job
    function createJob(
        address _provider,
        address _evaluator,
        uint256 _expiredAt,
        string calldata _description,
        address _hook
    ) external returns (uint256) {
        uint256 jobId = nextJobId++;
        jobs[jobId] = Job({
            id: jobId,
            client: msg.sender,
            provider: _provider,
            evaluator: _evaluator,
            expiredAt: _expiredAt,
            description: _description,
            hook: _hook,
            status: JobStatus.Open,
            reason: bytes32(0),
            budget: 0
        });
        emit JobCreated(jobId, msg.sender, _provider);
        return jobId;
    }

    /// @notice Set budget for a job (called by provider)
    function setBudget(uint256 _jobId, uint256 _amount, bytes calldata /*optParams*/) external {
        Job storage job = jobs[_jobId];
        require(job.id != 0, "Job does not exist");
        require(msg.sender == job.provider, "Only provider");
        require(job.status == JobStatus.Open, "Must be Open");
        job.budget = _amount;
        job.status = JobStatus.Funded;
        emit BudgetSet(_jobId, _amount);
    }

    /// @notice Fund a job (called by client to confirm payment)
    function fund(uint256 _jobId, bytes calldata /*optParams*/) external {
        Job storage job = jobs[_jobId];
        require(job.id != 0, "Job does not exist");
        require(msg.sender == job.client, "Only client");
        require(job.status == JobStatus.Funded, "Must be Funded");
        job.status = JobStatus.Submitted;
        emit JobFunded(_jobId);
    }

    /// @notice Submit deliverable (called by provider)
    function submit(uint256 _jobId, bytes32 _deliverable, bytes calldata /*optParams*/) external {
        Job storage job = jobs[_jobId];
        require(job.id != 0, "Job does not exist");
        require(msg.sender == job.provider, "Only provider");
        require(job.status == JobStatus.Submitted, "Must be Submitted");
        emit Submitted(_jobId, _deliverable);
    }

    /// @notice Complete a job (called by evaluator)
    function complete(uint256 _jobId, bytes32 _reason, bytes calldata /*optParams*/) external {
        Job storage job = jobs[_jobId];
        require(job.id != 0, "Job does not exist");
        require(msg.sender == job.evaluator, "Only evaluator");
        require(job.status == JobStatus.Submitted, "Must be Submitted");
        job.status = JobStatus.Completed;
        job.reason = _reason;
        emit Completed(_jobId, _reason);
    }

    /// @notice Reject a job (called by evaluator)
    function reject(uint256 _jobId, bytes32 _reason, bytes calldata /*optParams*/) external {
        Job storage job = jobs[_jobId];
        require(job.id != 0, "Job does not exist");
        require(msg.sender == job.evaluator, "Only evaluator");
        require(job.status == JobStatus.Submitted, "Must be Submitted");
        job.status = JobStatus.Rejected;
        job.reason = _reason;
        emit JobRejected(_jobId, _reason);
    }

    /// @notice Get job status
    function getJobStatus(uint256 _jobId) external view returns (uint8) {
        return uint8(jobs[_jobId].status);
    }

    /// @notice Transfer ownership
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Zero address");
        owner = _newOwner;
    }
}
