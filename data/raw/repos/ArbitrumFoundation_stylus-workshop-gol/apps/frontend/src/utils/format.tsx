/**
 * Formats an Ethereum address to a shorter version
 * @param address - The full Ethereum address
 * @returns Formatted address (e.g., 0x1234...5678)
 */
export const formatAddress = (address: string): string => {
  if (!address) return '';
  return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
};

/**
 * Copies text to clipboard
 * @param text - The text to copy
 * @returns Promise that resolves when text is copied
 */
export const copyToClipboard = async (text: string): Promise<void> => {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {

  }
};
