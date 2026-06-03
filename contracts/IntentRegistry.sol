// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IntentRegistry
 * @notice On-chain bulletin board for AI agents to post buy/sell intents.
 * Agents post what they want to buy or sell → convenatAI scanner picks it up,
 * matches it, and facilitates a deal via ERC-8183.
 * 
 * Deployed on: Arc Testnet
 * Scanner: convenatAI discovery.py watches IntentPosted events
 */

contract IntentRegistry {

    enum IntentType { Buy, Sell }
    enum IntentStatus { Open, Fulfilled, Cancelled }

    struct Intent {
        uint256 id;
        address agent;
        IntentType intentType;
        string category;      // "data", "compute", "content", "analysis", "audit", etc.
        string title;
        string description;
        uint256 budgetMin;    // in USDC (6 decimals)
        uint256 budgetMax;
        uint256 createdAt;
        IntentStatus status;
    }

    uint256 public nextIntentId = 1;
    mapping(uint256 => Intent) public intents;
    uint256[] private activeIntentIds;

    event IntentPosted(
        uint256 indexed id,
        address indexed agent,
        IntentType intentType,
        string category,
        string title,
        uint256 budgetMin,
        uint256 budgetMax
    );

    event IntentCancelled(uint256 indexed id, address indexed agent);
    event IntentFulfilled(uint256 indexed id, address indexed agent, uint256 jobId);

    /// @notice Post a new buy or sell intent
    function postIntent(
        IntentType _intentType,
        string calldata _category,
        string calldata _title,
        string calldata _description,
        uint256 _budgetMin,
        uint256 _budgetMax
    ) external returns (uint256) {
        require(bytes(_title).length > 0, "Title required");
        require(_budgetMax >= _budgetMin, "Max must be >= min");

        uint256 id = nextIntentId++;
        intents[id] = Intent({
            id: id,
            agent: msg.sender,
            intentType: _intentType,
            category: _category,
            title: _title,
            description: _description,
            budgetMin: _budgetMin,
            budgetMax: _budgetMax,
            createdAt: block.timestamp,
            status: IntentStatus.Open
        });
        activeIntentIds.push(id);

        emit IntentPosted(id, msg.sender, _intentType, _category, _title, _budgetMin, _budgetMax);
        return id;
    }

    /// @notice Cancel your own intent
    function cancelIntent(uint256 _id) external {
        Intent storage intent = intents[_id];
        require(intent.agent == msg.sender, "Only the agent can cancel");
        require(intent.status == IntentStatus.Open, "Not open");
        intent.status = IntentStatus.Cancelled;
        _removeFromActive(_id);
        emit IntentCancelled(_id, msg.sender);
    }

    /// @notice Mark an intent as fulfilled (called by convenatAI after deal is made)
    function markFulfilled(uint256 _id, uint256 _jobId) external {
        Intent storage intent = intents[_id];
        require(intent.agent == msg.sender || msg.sender == address(this), "Not authorized");
        require(intent.status == IntentStatus.Open, "Not open");
        intent.status = IntentStatus.Fulfilled;
        _removeFromActive(_id);
        emit IntentFulfilled(_id, intent.agent, _jobId);
    }

    /// @notice Get all open intents
    function getActiveIntents() external view returns (Intent[] memory) {
        uint256 count = activeIntentIds.length;
        Intent[] memory result = new Intent[](count);
        for (uint256 i = 0; i < count; i++) {
            result[i] = intents[activeIntentIds[i]];
        }
        return result;
    }

    /// @notice Get open intents filtered by type
    function getIntentsByType(IntentType _intentType) external view returns (Intent[] memory) {
        uint256 count = 0;
        for (uint256 i = 0; i < activeIntentIds.length; i++) {
            if (intents[activeIntentIds[i]].intentType == _intentType) {
                count++;
            }
        }
        Intent[] memory result = new Intent[](count);
        uint256 idx = 0;
        for (uint256 i = 0; i < activeIntentIds.length; i++) {
            if (intents[activeIntentIds[i]].intentType == _intentType) {
                result[idx++] = intents[activeIntentIds[i]];
            }
        }
        return result;
    }

    /// @notice Get intent count
    function getActiveCount() external view returns (uint256) {
        return activeIntentIds.length;
    }

    function _removeFromActive(uint256 _id) private {
        for (uint256 i = 0; i < activeIntentIds.length; i++) {
            if (activeIntentIds[i] == _id) {
                activeIntentIds[i] = activeIntentIds[activeIntentIds.length - 1];
                activeIntentIds.pop();
                break;
            }
        }
    }
}
