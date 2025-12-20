// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

interface IGameOfLifeNFT {
    function tokenURI(uint256 tokenId) external view returns (string memory);
}

contract NFT is ERC721, Ownable {
    using Strings for uint256;
    // Keep track of all tokens
    uint256[] private _allTokens;
    
    // Rust contract address
    address private constant GAME_OF_LIFE_CONTRACT = 0x1B9CbDC65a7BebB0bE7F18d93A1896ea1FD46d7A;

    constructor(address initialOwner) ERC721("MyNFT", "MNFT") Ownable(initialOwner) {}

    function mint() public returns (uint256) {
        uint256 tokenId = _allTokens.length + 1;
        _allTokens.push(tokenId);
        _safeMint(msg.sender, tokenId);
        return tokenId;
    }

    function totalSupply() public view returns (uint256) {
        // TODO: Implement this method
        return 0;
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        // Ensure the token exists
        _requireOwned(tokenId);
        
        // Ensure tokenId is positive
        require(tokenId > 0, "Token ID must be a positive integer");

        // Constants matching Rust implementation
        uint256 size = 8;
        uint256 generations = 4;
        
        // Use tokenId as seed
        uint256 seed = tokenId;

        // Start SVG string with viewBox matching grid size
        string memory svg = string.concat(
            "<svg viewBox=\"0 0 ",
            Strings.toString(size),
            " ",
            Strings.toString(size),
            "\" xmlns=\"http://www.w3.org/2000/svg\"><style>",
            "@keyframes gol_pulse {0% {opacity:0}20% {opacity:1}80% {opacity:1}100% {opacity:0}}",
            "@keyframes gol_last {0% {opacity:0}20% {opacity:1}100% {opacity:1}}",
            ".gol-cell {fill:#000;opacity:0;animation:gol_pulse 500ms forwards}",
            ".gol-cell.last {animation:gol_last 500ms forwards}",
            "</style>"
        );

        // Initialize first generation from seed
        bool[][] memory grid = new bool[][](size);
        for (uint256 y = 0; y < size; y++) {
            grid[y] = new bool[](size);
            for (uint256 x = 0; x < size; x++) {
                uint256 v = ((x ^ y) + ((x | y) & (size - 1)) + seed) & (size - 1);
                if (v < size / 3) {
                    grid[y][x] = true;
                    svg = string.concat(
                        svg,
                        "<rect class=\"gol-cell\" x=\"",
                        Strings.toString(x),
                        "\" y=\"",
                        Strings.toString(y),
                        "\" width=\"0.9\" height=\"0.9\"/>"
                    );
                }
            }
        }

        // Compute and render next generations
        bool hasLiveCells = true;
        for (uint256 gen = 1; gen < generations && hasLiveCells; gen++) {
            bool[][] memory next = new bool[][](size);
            hasLiveCells = false;

            for (uint256 y = 0; y < size; y++) {
                next[y] = new bool[](size);
                for (uint256 x = 0; x < size; x++) {
                    uint256 neighbors = 0;
                    
                    // Count neighbors (including wrapping)
                    for (int8 dy = -1; dy <= 1; dy++) {
                        for (int8 dx = -1; dx <= 1; dx++) {
                            if (dx == 0 && dy == 0) continue;
                            
                            // Safe neighbor calculation without type casting or arithmetic
                            uint256 nx;
                            uint256 ny;
                            
                            // Handle x-axis wrapping
                            if (dx == -1) {
                                nx = x == 0 ? size - 1 : x - 1;
                            } else if (dx == 1) {
                                nx = x == size - 1 ? 0 : x + 1;
                            } else {
                                nx = x;
                            }
                            
                            // Handle y-axis wrapping
                            if (dy == -1) {
                                ny = y == 0 ? size - 1 : y - 1;
                            } else if (dy == 1) {
                                ny = y == size - 1 ? 0 : y + 1;
                            } else {
                                ny = y;
                            }
                            
                            if (grid[ny][nx]) {
                                neighbors++;
                            }
                        }
                    }

                    // Apply Game of Life rules
                    next[y][x] = (grid[y][x] && (neighbors == 2 || neighbors == 3)) || 
                                (!grid[y][x] && neighbors == 3);

                    if (next[y][x]) {
                        hasLiveCells = true;
                        bool isLast = gen == generations - 1;
                        
                        svg = string.concat(
                            svg,
                            "<rect class=\"gol-cell",
                            isLast ? " last" : "",
                            "\" x=\"",
                            Strings.toString(x),
                            "\" y=\"",
                            Strings.toString(y),
                            "\" width=\"0.9\" height=\"0.9\"",
                            "\" style=\"animation-delay:",
                            Strings.toString(gen * 400),
                            "ms\"/>"
                        );
                    }
                }
            }
            grid = next;
        }

        svg = string.concat(svg, "</svg>");
        return svg;
    }

}
