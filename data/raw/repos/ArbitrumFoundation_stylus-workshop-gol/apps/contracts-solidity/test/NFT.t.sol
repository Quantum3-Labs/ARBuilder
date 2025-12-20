// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import { PRBTest } from "@prb/test/src/PRBTest.sol";
import { console2 } from "forge-std/src/console2.sol";
import { StdCheats } from "forge-std/src/StdCheats.sol";

import "../src/NFT.sol"; // Importing the NFT contract

contract NFTTest is PRBTest, StdCheats {
    NFT private nft;
    address owner = address(1);

    function setUp() public {
        nft = new NFT(owner); // Deploy a new instance of the NFT contract before each test
    }

    function testMint() public {
        vm.prank(owner);
        uint256 tokenId = nft.mint();
        assertEq(nft.ownerOf(tokenId), owner);
    }

    
}