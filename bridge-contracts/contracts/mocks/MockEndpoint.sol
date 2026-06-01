// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

struct Origin {
    uint32 srcEid;
    bytes32 sender;
    uint64 nonce;
}

interface OAppReceiver {
    function lzReceive(
        Origin calldata _origin,
        bytes32 _guid,
        bytes calldata _message,
        address _executor,
        bytes calldata _extraData
    ) external payable;
}

contract MockEndpoint {
    function setDelegate(address /*_delegate*/) external {}
    
    function simulateReceive(
        address _receiver,
        Origin calldata _origin,
        bytes32 _guid,
        bytes calldata _message,
        address _executor,
        bytes calldata _extraData
    ) external payable {
        OAppReceiver(_receiver).lzReceive{value: msg.value}(
            _origin,
            _guid,
            _message,
            _executor,
            _extraData
        );
    }
}
