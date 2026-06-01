// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import { OApp, Origin } from "@layerzerolabs/oapp-evm/contracts/oapp/OApp.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";

interface IAgenticCommerce {
    function reject(
        uint256 jobId,
        bytes32 reason,
        bytes calldata optParams
    ) external;
}

/**
 * @title BridgeReceiver
 * @dev GenLayer SLA breach receiver deployed on Arc Testnet.
 * Receives LayerZero messages from ZKsync Sepolia and executes the on-chain Kill-Switch.
 */
contract BridgeReceiver is OApp {
    
    address public agenticCommerce;

    event SLABreachReceived(uint256 indexed jobId, string reason, bytes32 guid);
    event AgenticCommerceAddressUpdated(address indexed oldAddress, address indexed newAddress);

    constructor(
        address _endpoint,
        address _delegate,
        address _agenticCommerce
    ) OApp(_endpoint, _delegate) Ownable(_delegate) {
        agenticCommerce = _agenticCommerce;
    }

    /**
     * @notice Set/Update the target Agentic Commerce (ERC-8183) contract address.
     * @param _agenticCommerce The new AgenticCommerce contract address.
     */
    function setAgenticCommerce(address _agenticCommerce) external onlyOwner {
        emit AgenticCommerceAddressUpdated(agenticCommerce, _agenticCommerce);
        agenticCommerce = _agenticCommerce;
    }

    /**
     * @notice Internal function to receive and process LayerZero messages.
     * @param _origin The LZ Origin metadata.
     * @param _guid The unique LZ transaction GUID.
     * @param _message The received payload encoded as (uint256, string).
     */
    function _lzReceive(
        Origin calldata _origin,
        bytes32 _guid,
        bytes calldata _message,
        address /*_executor*/,
        bytes calldata /*_extraData*/
    ) internal override {
        // Decode the payload
        (uint256 jobId, string memory reason) = abi.decode(_message, (uint256, string));
        
        emit SLABreachReceived(jobId, reason, _guid);

        // Convert string reason to bytes32 hash as required by ERC-8183
        bytes32 reasonHash = keccak256(abi.encodePacked(reason));

        // Call the reject function on the Arc ERC-8183 AgenticCommerce contract
        IAgenticCommerce(agenticCommerce).reject(
            jobId,
            reasonHash,
            new bytes(0) // Empty optional parameters
        );
    }
}
