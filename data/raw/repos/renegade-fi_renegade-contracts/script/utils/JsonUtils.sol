// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable gas-increment-by-one */
/* solhint-disable gas-strict-inequalities */

import { Vm } from "forge-std/Vm.sol";

/// @title JsonUtils
/// @author Renegade Eng
/// @notice Utility library for JSON file manipulation in deployment scripts
library JsonUtils {
    /// @notice Write a key-value pair to a JSON file, handling existing entries
    /// @param vm The VM to run the commands with
    /// @param filePath The path to the JSON file
    /// @param key The key to write
    /// @param value The value to write
    function writeJsonEntry(Vm vm, string memory filePath, string memory key, string memory value) internal {
        // Read existing file if it exists
        string memory jsonContent = "";
        try vm.readFile(filePath) returns (string memory content) {
            jsonContent = content;
        } catch {
            // File doesn't exist yet, start with empty object
            jsonContent = "{}";
        }

        // Parse existing entries into a map
        string[] memory entries = parseJsonEntries(jsonContent);

        // Create new entries array with updated/added entry
        string[] memory newEntries = new string[](entries.length + 1);
        bool found = false;

        // Copy existing entries, replacing if key matches
        for (uint256 i = 0; i < entries.length; i++) {
            string memory entry = entries[i];
            if (bytes(entry).length == 0) continue;

            string memory currentKey = extractKey(entry);
            if (keccak256(bytes(currentKey)) == keccak256(bytes(key))) {
                newEntries[i] = string(abi.encodePacked("\"", key, "\":\"", value, "\""));
                found = true;
            } else {
                newEntries[i] = entry;
            }
        }

        // Add new entry if not found
        if (!found) {
            newEntries[entries.length] = string(abi.encodePacked("\"", key, "\":\"", value, "\""));
        }

        // Construct new JSON
        string memory newJson = "{";
        for (uint256 i = 0; i < newEntries.length; i++) {
            if (bytes(newEntries[i]).length == 0) continue;
            if (i > 0 && bytes(newEntries[i - 1]).length > 0) {
                newJson = string(abi.encodePacked(newJson, ","));
            }
            newJson = string(abi.encodePacked(newJson, newEntries[i]));
        }
        newJson = string(abi.encodePacked(newJson, "}"));

        // Write back to file
        vm.writeFile(filePath, newJson);
    }

    /// @notice Parse JSON string into array of key-value entries
    /// @param json The JSON string to parse
    /// @return Array of key-value entry strings
    function parseJsonEntries(string memory json) internal pure returns (string[] memory) {
        // Remove whitespace and outer braces
        string memory cleaned = cleanJson(json);
        if (bytes(cleaned).length <= 2) return new string[](0);

        // Split by commas
        string[] memory entries = splitByComma(substring(cleaned, 1, bytes(cleaned).length - 1));
        return entries;
    }

    /// @notice Extract key from a JSON entry
    /// @param entry The JSON entry string
    /// @return The extracted key
    function extractKey(string memory entry) internal pure returns (string memory) {
        uint256 colonPos = findChar(entry, ":");
        if (colonPos == 0) return "";

        string memory key = substring(entry, 0, colonPos);
        // Remove quotes
        if (bytes(key).length >= 2 && bytes(key)[0] == "\"" && bytes(key)[bytes(key).length - 1] == "\"") {
            return substring(key, 1, bytes(key).length - 1);
        }
        return key;
    }

    /// @notice Split string by commas, respecting quotes
    /// @param str The string to split
    /// @return Array of substrings
    function splitByComma(string memory str) internal pure returns (string[] memory) {
        bytes memory strBytes = bytes(str);
        bool inQuotes = false;
        uint256 count = 1;

        // Count number of top-level commas
        for (uint256 i = 0; i < strBytes.length; i++) {
            if (strBytes[i] == "\"") {
                inQuotes = !inQuotes;
            } else if (strBytes[i] == "," && !inQuotes) {
                count++;
            }
        }

        // Create array and split
        string[] memory parts = new string[](count);
        uint256 partIndex = 0;
        uint256 lastIndex = 0;
        inQuotes = false;

        for (uint256 i = 0; i < strBytes.length; i++) {
            if (strBytes[i] == "\"") {
                inQuotes = !inQuotes;
            } else if (strBytes[i] == "," && !inQuotes) {
                parts[partIndex] = substring(str, lastIndex, i);
                lastIndex = i + 1;
                partIndex++;
            }
        }

        // Add last part
        if (lastIndex < strBytes.length) {
            parts[partIndex] = substring(str, lastIndex, strBytes.length);
        }

        return parts;
    }

    /// @notice Clean up a JSON string by removing whitespace
    /// @param json The JSON string to clean
    /// @return The cleaned JSON string
    function cleanJson(string memory json) internal pure returns (string memory) {
        bytes memory jsonBytes = bytes(json);
        bytes memory cleaned = new bytes(jsonBytes.length);
        uint256 cleanedLength = 0;
        bool inQuotes = false;

        for (uint256 i = 0; i < jsonBytes.length; i++) {
            bytes1 char = jsonBytes[i];

            if (char == "\"") {
                inQuotes = !inQuotes;
            }

            if (inQuotes || (char != " " && char != "\n" && char != "\r" && char != "\t")) {
                cleaned[cleanedLength] = char;
                cleanedLength++;
            }
        }

        bytes memory result = new bytes(cleanedLength);
        for (uint256 i = 0; i < cleanedLength; i++) {
            result[i] = cleaned[i];
        }

        return string(result);
    }

    /// @notice Helper function to find a character in a string
    /// @param str The string to search
    /// @param char The character to find
    /// @return The index of the character, or 0 if not found
    function findChar(string memory str, bytes1 char) internal pure returns (uint256) {
        bytes memory strBytes = bytes(str);
        for (uint256 i = 0; i < strBytes.length; i++) {
            if (strBytes[i] == char) {
                return i;
            }
        }
        return 0;
    }

    /// @notice Helper function to get a substring
    /// @param str The source string
    /// @param startIndex The start index (inclusive)
    /// @param endIndex The end index (exclusive)
    /// @return The extracted substring
    function substring(string memory str, uint256 startIndex, uint256 endIndex) internal pure returns (string memory) {
        bytes memory strBytes = bytes(str);
        bytes memory result = new bytes(endIndex - startIndex);
        for (uint256 i = startIndex; i < endIndex; i++) {
            result[i - startIndex] = strBytes[i];
        }
        return string(result);
    }
}
