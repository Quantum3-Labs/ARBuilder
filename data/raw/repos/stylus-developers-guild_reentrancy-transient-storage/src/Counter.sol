// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

contract Token {
    function invoke() external {
        Counter(msg.sender).kickoff(this);
    }
}

contract Counter {
    uint256 public counter;

    function kickoff(Token _invoker) external returns (uint256) {
        if (msg.sender == address(_invoker)) {
            counter++;
        } else {
            _invoker.invoke();
        }
        return counter;
    }
}
