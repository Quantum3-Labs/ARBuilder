// Contract addresses
export const CONTRACT_ADDRESSES = {
  RUST_NFT: '0xa6e41ffd769491a42a6e5ce453259b93983a22ef',
  SOLIDITY_NFT: '0x7E32b54800705876d3b5cFbc7d9c226a211F7C1a',
  SOLIDITY_AND_STYLUS_NFT: '0x525c2aBA45F66987217323E8a05EA400C65D06DC',
} as const;

// Contract ABIs (if needed in the future)
export const CONTRACT_ABIS = {
  // Add ABIs here when needed
} as const;

// Contract names for UI display
export const CONTRACT_NAMES = {
  [CONTRACT_ADDRESSES.RUST_NFT]: 'Rust Stylus NFT',
  [CONTRACT_ADDRESSES.SOLIDITY_NFT]: 'Solidity NFT',
  [CONTRACT_ADDRESSES.SOLIDITY_AND_STYLUS_NFT]: 'Solidity + Stylus NFT',
} as const;

export type ContractName = keyof typeof CONTRACT_NAMES;
