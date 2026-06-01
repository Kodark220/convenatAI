// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import { OApp, MessagingFee, Origin } from "@layerzerolabs/oapp-evm/contracts/oapp/OApp.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title BridgeForwarder
 * @dev GenLayer SLA breach forwarder deployed on ZKsync Era Sepolia.
 * Uses LayerZero v2 to send cross-chain kill-switch notifications to Arc Testnet.
 */
contract BridgeForwarder is OApp {
    
    event SLABreachForwarded(uint32 indexed dstEid, uint256 indexed jobId, string reason, bytes32 transferId);

    constructor(address _endpoint, address _delegate) OApp(_endpoint, _delegate) Ownable(_delegate) {}

    /**
     * @notice Forward an SLA breach event detected by GenLayer to Arc Testnet.
     * @param _dstEid LayerZero Endpoint ID of the destination chain (Arc Testnet).
     * @param _jobId The target ERC-8183 job ID to reject.
     * @param _reason The SLA breach reasoning from GenLayer QA evaluation.
     * @param _options Execution options for LayerZero executor.
     */
    function forwardSLABreach(
        uint32 _dstEid,
        uint256 _jobId,
        string calldata _reason,
        bytes calldata _options
    ) external payable {
        bytes memory payload = abi.encode(_jobId, _reason);
        
        // LZ v2 send call
        MessagingFee memory fee = MessagingFee(msg.value, 0);
        bytes32 transferId = _lzSend(
            _dstEid,
            payload,
            _options,
            fee,
            payable(msg.sender)
        ).guid;

        emit SLABreachForwarded(_dstEid, _jobId, _reason, transferId);
    }

    /**
     * @notice Quote the LayerZero cross-chain delivery fee.
     * @param _dstEid Destination chain EID.
     * @param _jobId Target job ID.
     * @param _reason SLA breach reason.
     * @param _options LZ executor options.
     */
    function quote(
        uint32 _dstEid,
        uint256 _jobId,
        string calldata _reason,
        bytes calldata _options
    ) external view returns (uint256 nativeFee, uint256 lzTokenFee) {
        bytes memory payload = abi.encode(_jobId, _reason);
        MessagingFee memory fee = _quote(_dstEid, payload, _options, false);
        return (fee.nativeFee, fee.lzTokenFee);
    }

    // Required override by standard LZ OApp to receive messages (forwarder doesn't receive, but must compile)
    function _lzReceive(
        Origin calldata /*_origin*/,
        bytes32 /*_guid*/,
        bytes calldata /*_message*/,
        address /*_executor*/,
        bytes calldata /*_extraData*/
    ) internal override {}
}
