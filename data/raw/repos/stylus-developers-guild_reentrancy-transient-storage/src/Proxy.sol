// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

contract Proxy {
    address public immutable FACET_HELLO;
    address public immutable FACET_REENTRANT;

    constructor(address _hello, address _reentrant) {
        FACET_HELLO = _hello;
        FACET_REENTRANT = _reentrant;
    }

    function directDelegate(address to) internal {
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), to, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 {
                revert(0, returndatasize())
            }
            default {
                return(0, returndatasize())
            }
        }
    }

    function hello() public returns (uint256) {
        directDelegate(FACET_HELLO);
    }

    function reentrant() external returns (uint256) {
        directDelegate(FACET_REENTRANT);
    }
}
