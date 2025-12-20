---
url: https://docs.arbitrum.io/for-devs/quickstart-solidity-hardhat
title: Build a decentralized app with Solidity (Quickstart) | Arbitrum Docs
category: arbitrum_docs
subcategory: general
scraped_at: 2025-12-20T10:42:26.791455
---

[Skip to main content](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#__docusaurus_skipToContent_fallback)
Reactivate your Stylus contracts to ensure they remain callable - [here’s how to do it.](https://docs.arbitrum.io/stylus/gentle-introduction#activation)
[ ![Arbitrum Logo](https://docs.arbitrum.io/img/logo.svg)![Arbitrum Logo](https://docs.arbitrum.io/img/logo.svg) **Arbitrum Docs**](https://docs.arbitrum.io/get-started/overview)
[Get started](https://docs.arbitrum.io/get-started/overview)
[Build apps](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix)
  * [Build with Solidity](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix)
  * [Build with Stylus](https://docs.arbitrum.io/stylus/quickstart)


[Launch a chain](https://docs.arbitrum.io/launch-arbitrum-chain/a-gentle-introduction)[Run a node](https://docs.arbitrum.io/run-arbitrum-node/overview)[Use the bridge](https://docs.arbitrum.io/arbitrum-bridge/quickstart)[How it works](https://docs.arbitrum.io/how-arbitrum-works/inside-arbitrum-nitro)[Notices](https://docs.arbitrum.io/notices/fusaka-upgrade-notice)
  * [Build apps with Solidity](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix)
    * [Quickstart](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix)
    * [Estimate gas](https://docs.arbitrum.io/build-decentralized-apps/how-to-estimate-gas)
    * [Chains and testnets](https://docs.arbitrum.io/build-decentralized-apps/public-chains)
    * [Cross-chain messaging](https://docs.arbitrum.io/build-decentralized-apps/cross-chain-messaging)
    * [Custom gas token SDK](https://docs.arbitrum.io/build-decentralized-apps/custom-gas-token-sdk)
    * [Arbitrum vs Ethereum](https://docs.arbitrum.io/build-decentralized-apps/arbitrum-vs-ethereum/comparison-overview)
    * [Oracles](https://docs.arbitrum.io/build-decentralized-apps/oracles/overview-oracles)
    * [Precompiles](https://docs.arbitrum.io/build-decentralized-apps/precompiles/overview)
    * [NodeInterface](https://docs.arbitrum.io/build-decentralized-apps/nodeinterface/overview)
    * [Token bridging](https://docs.arbitrum.io/build-decentralized-apps/token-bridging/overview)
    * [Reference](https://docs.arbitrum.io/build-decentralized-apps/reference/node-providers)
    * [Troubleshooting](https://docs.arbitrum.io/for-devs/troubleshooting-building)
    * [Arbitrum SDK](https://docs.arbitrum.io/sdk/)
  * [Build apps with Stylus](https://docs.arbitrum.io/stylus/gentle-introduction)
  * [Chain Info↑](https://docs.arbitrum.io/for-devs/dev-tools-and-resources/chain-info)
  * [Glossary↑](https://docs.arbitrum.io/intro/glossary)
  * [Contribute↑](https://docs.arbitrum.io/for-devs/contribute)


On this page
# Build a decentralized app with Solidity (Quickstart)
Head over to [the Stylus quickstart](https://docs.arbitrum.io/stylus/quickstart) if you'd like to use Rust instead of Solidity.
This quickstart is for web developers who want to start building **decentralized applications** using Arbitrum. It makes no assumptions about your prior experience with Ethereum, Arbitrum, or Solidity. Familiarity with Javascript and yarn is expected. If you're new to Ethereum, consider studying the 
### What we'll learn[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#what-well-learn "Direct link to What we'll learn")
In this tutorial we will learn:
  1. The basics of Ethereum vs. client/server architecture
  2. What is a Solidity smart contract
  3. How to compile and deploy a smart contract
  4. How to use an Ethereum wallet


We're going to build a digital cupcake vending machine using Solidity smart contracts[1](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fn-1). This vending machine will follow two rules:
  1. The vending machine will distribute a cupcake to anyone who hasn't recently received one.
  2. The vending machine's rules can't be changed by anyone.


Here's the vending machine implemented with Javascript. To use it, enter a name in the form below and press the **Cupcake please!** button, you should see your cupcake balance go up.
#### Free Cupcakes
web2NameContract addressCupcake please!Refresh balance🧁
Cupcake balance:0 (no name)
We can assume that this vending machine operates as we expect, but it's largely up to the **centralized service provider** that hosts it. In the case of a compromised cloud host:
  1. Our centralized service provider can deny access to particular users.
  2. A malicious actor can change the rules of the vending machine at any time, for example, to give their friends extra cupcakes.


Centralized third-party intermediaries represent a **single point of failure** that malicious actors can exploit. With a blockchain infrastructure such as Ethereum, we decentralize our vending machine's **business logic and data** , making this type of exploits nearly impossible.
This is Arbitrum's core value proposition to you, dear developer. Arbitrum makes it easy for you to deploy your vending machines to Ethereum's permissionless, trustless, decentralized network of nodes[2](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fn-2) **while keeping costs low for you and your users**.
Let's implement the "Web3" version of the above vending machine using Arbitrum.
### Prerequisites[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#prerequisites "Direct link to Prerequisites")
VS Code
VS Code is the IDE we'll use to build our vending machine. See 
Web3 wallet
We will use Metamask as the wallet to interact with our vending machine. See 
Yarn
Yarn is the package manager we'll use to install dependencies. See 
Foundry
Foundry is the toolchain we'll use to compile and deploy our smart contract. See 
We'll address any remaining dependencies as we go.
### Ethereum and Arbitrum in a nutshell[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#ethereum-and-arbitrum-in-a-nutshell "Direct link to Ethereum and Arbitrum in a nutshell")
  * **Ethereum**
    * Ethereum is a decentralized network of blockchain data structure.
    * The data within Ethereum's blockchain data structure changes one transaction at a time.
    * Smart contracts are small programs that execute transactions according to predefined rules. Ethereum's nodes host and execute smart contracts.
    * You can use smart contracts to build decentralized apps that use Ethereum's network to process transactions and store data. Think of smart contracts as your app's backend
    * Apps let users carry their data and identity between applications without trusting centralized service providers.
    * People who run Ethereum validator nodes[3](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fn-3) can earn `ETH` for processing and validating transactions on behalf of users and apps.
    * These transactions can be expensive when the network is under heavy load.
  * **Arbitrum**
    * Arbitrum is a suite of child chain scaling solutions for app developers.
    * Arbitrum One is a child chain that implements the Arbitrum Rollup protocol.
    * You can use Arbitrum One to build user-friendly apps with high throughput, low latency, and low transaction costs while inheriting Ethereum's high-security standards[4](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fn-4).


### Review the Javascript vending machine[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#review-the-javascript-vending-machine "Direct link to Review the Javascript vending machine")
Here's the vending machine implemented as a Javascript class:
VendingMachine.js
```
class VendingMachine {  
  // state variables = internal memory of the vending machine  
  cupcakeBalances = {};  
  cupcakeDistributionTimes = {};  
  
  // Vend a cupcake to the caller  
  giveCupcakeTo(userId) {  
    if (this.cupcakeDistributionTimes[userId] === undefined) {  
      this.cupcakeBalances[userId] = 0;  
      this.cupcakeDistributionTimes[userId] = 0;  
    }  
  
    // Rule 1: The vending machine will distribute a cupcake to anyone who hasn't recently received one.  
    const fiveSeconds = 5000;  
    const userCanReceiveCupcake = this.cupcakeDistributionTimes[userId] + fiveSeconds <= Date.now();  
    if (userCanReceiveCupcake) {  
      this.cupcakeBalances[userId]++;  
      this.cupcakeDistributionTimes[userId] = Date.now();  
      console.log(`Enjoy your cupcake, ${userId}!`);  
      return true;  
    } else {  
      console.error(  
        'HTTP 429: Too Many Cupcakes (you must wait at least 5 seconds between cupcakes)',  
      );  
      return false;  
    }  
  }  
  
  getCupcakeBalanceFor(userId) {  
    return this.cupcakeBalances[userId];  
  }  
}  

```

The `VendingMachine` class uses _state variables_ and _functions_ to implement _predefined rules_. This implementation is useful because it automates cupcake distribution, but there's a problem: it's hosted by a centralized server controlled by a third-party service provider.
Let's decentralize our vending machine's business logic and data by porting the above JavaScript implementation into a Solidity smart contract.
### Review the Solidity vending machine[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#review-the-solidity-vending-machine "Direct link to Review the Solidity vending machine")
Here is a Solidity implementation of the vending machine. Solidity is a language that compiles to Arbitrum One, and Arbitrum Nova.
VendingMachine.sol
```
// SPDX-License-Identifier: MIT  
// Specify the Solidity compiler version - this contract requires version 0.8.9 or higher  
pragma solidity ^0.8.9;  
  
// Define a smart contract named VendingMachine  
// Unlike regular classes, once deployed, this contract's code cannot be modified  
// This ensures that the vending machine's rules remain constant and trustworthy  
contract VendingMachine {  
   // State variables are permanently stored in blockchain storage  
   // These mappings associate Ethereum addresses with unsigned integers  
   // The 'private' keyword means these variables can only be accessed from within this contract  
   mapping(address => uint) private _cupcakeBalances;     // Tracks how many cupcakes each address owns  
   mapping(address => uint) private _cupcakeDistributionTimes;  // Tracks when each address last received a cupcake  
  
   // Function to give a cupcake to a specified address  
   // 'public' means this function can be called by anyone  
   // 'returns (bool)' specifies that the function returns a boolean value  
   function giveCupcakeTo(address userAddress) public returns (bool) {  
       // Initialize first-time users  
       // In Solidity, uninitialized values default to 0, so this check isn't strictly necessary  
       // but is included to mirror the JavaScript implementation  
       if (_cupcakeDistributionTimes[userAddress] == 0) {  
           _cupcakeBalances[userAddress] = 0;  
           _cupcakeDistributionTimes[userAddress] = 0;  
       }  
  
       // Calculate when the user is eligible for their next cupcake  
       // 'seconds' is a built-in time unit in Solidity  
       // 'block.timestamp' gives us the current time in seconds since Unix epoch  
       uint fiveSecondsFromLastDistribution = _cupcakeDistributionTimes[userAddress] + 5 seconds;  
       bool userCanReceiveCupcake = fiveSecondsFromLastDistribution <= block.timestamp;  
  
       if (userCanReceiveCupcake) {  
           // If enough time has passed, give them a cupcake and update their last distribution time  
           _cupcakeBalances[userAddress]++;  
           _cupcakeDistributionTimes[userAddress] = block.timestamp;  
           return true;  
       } else {  
           // If not enough time has passed, revert the transaction with an error message  
           // 'revert' cancels the transaction and returns the error message to the user  
           revert("HTTP 429: Too Many Cupcakes (you must wait at least 5 seconds between cupcakes)");  
       }  
   }  
  
   // Function to check how many cupcakes an address owns  
   // 'public' means anyone can call this function  
   // 'view' means this function only reads data and doesn't modify state  
   // This makes it free to call (no gas cost) when called externally  
   function getCupcakeBalanceFor(address userAddress) public view returns (uint) {  
       return _cupcakeBalances[userAddress];  
   }  
}  

```

### Compile your smart contract with Remix[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#compile-your-smart-contract-with-remix "Direct link to Compile your smart contract with Remix")
Smart contracts need to be compiled to bytecode to be stored and executed onchain by the EVM; we'll use Remix to do that.
Remix is a browser-based IDE for EVM development. There are other IDEs to choose from (Foundry, Hardhat), but Remix doesn't require any local environment setup, so we'll use it for this tutorial.
Let's first add our smart contract to Remix following these steps:
#### 1. Load Remix: [​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#1-load-remix-httpsremixethereumorg "Direct link to 1-load-remix-httpsremixethereumorg")
#### 2. Create a blank workspace in Remix:[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#2-create-a-blank-workspace-in-remix "Direct link to 2. Create a blank workspace in Remix:")
File explorer > Workspaces > Create blank
![](https://docs.arbitrum.io/img/apps-remix-create-blank-project-2025-01-07.gif)
#### 3. Copy your vending machine contract[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#3-copy-your-vending-machine-contract "Direct link to 3. Copy your vending machine contract")
#### 4. Paste your contract in Remix[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#4-paste-your-contract-in-remix "Direct link to 4. Paste your contract in Remix")
Select vending machine contract > Click compile menu > Compile
![](https://docs.arbitrum.io/img/apps-remix-paste-vending-machine-contract-2025-01-07.gif)
"File explorer > New file"
#### 5. Compile your contract in Remix[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#5-compile-your-contract-in-remix "Direct link to 5. Compile your contract in Remix")
Select vending machine contract > Click compile menu > Compile
![](https://docs.arbitrum.io/img/apps-remix-compile-contract-2025-01-07.gif)
Note
Ensure that Remix's compiler version matches the one in your contract. You can find your contract's compiler version at the top of your contract's file. It looks like this:
```
pragma solidity ^0.8.2;  

```

You can easily select the right compiler version in Remix's the "Solidity compiler" menu.
### Deploy the smart contract to a local Ethereum chain[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#deploy-the-smart-contract-to-a-local-ethereum-chain "Direct link to Deploy the smart contract to a local Ethereum chain")
Once a smart contract gets compiled, it is deployable to a blockchain. The safest way to do this is to deploy it to a locally hosted chain, where you can test and debug your contract before deploying it to a public chain.
To deploy our `VendingMachine` smart contract locally, we will:
  1. Run Foundry's local Ethereum node in a terminal window
  2. Configure a wallet so we can interact with our smart contract after deployment (1)
  3. Deploy our smart contract to (1)'s node using Remix


#### Run a local chain[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#run-a-local-chain "Direct link to Run a local chain")
Here, we'll use 
```
curl -L https://foundry.paradigm.xyz | bash && anvil  

```

Once you've run the above commands, you should see a prompt showing what test accounts automatically were generated for you and other infos about your local Anvil testnet.
```
                            (_) | |  
      __ _   _ __   __   __  _  | |  
     / _` | | '_ \  \ \ / / | | | |  
    | (_| | | | | |  \ V /  | | | |  
     \__,_| |_| |_|   \_/   |_| |_|  
  
    0.2.0 (7f0f5b4 2024-08-08T00:19:07.020431000Z)  
    https://github.com/foundry-rs/foundry  
  
# Available Accounts  
  
(0) 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000.000000000000000000 ETH)  
(1) 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (10000.000000000000000000 ETH)  
(2) 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC (10000.000000000000000000 ETH)  
(3) 0x90F79bf6EB2c4f870365E785982E1f101E93b906 (10000.000000000000000000 ETH)  
(4) 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65 (10000.000000000000000000 ETH)  
(5) 0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc (10000.000000000000000000 ETH)  
(6) 0x976EA74026E726554dB657fA54763abd0C3a0aa9 (10000.000000000000000000 ETH)  
(7) 0x14dC79964da2C08b23698B3D3cc7Ca32193d9955 (10000.000000000000000000 ETH)  
(8) 0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f (10000.000000000000000000 ETH)  
(9) 0xa0Ee7A142d267C1f36714E4a8F75612F20a79720 (10000.000000000000000000 ETH)  
  
# Private Keys  
  
(0) 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80  
(1) 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d  
(2) 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a  
(3) 0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6  
(4) 0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a  
(5) 0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba  
(6) 0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e  
(7) 0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356  
(8) 0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97  
(9) 0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6  
  
# Wallet  
  
Mnemonic: test test test test test test test test test test test junk  
Derivation path: m/44'/60'/0'/0/  
  
# Chain ID  
  
31337.  

```

#### Configure Metamask[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#configure-metamask "Direct link to Configure Metamask")
Next, open Metamask and create or import a wallet by following the displayed instructions.
By default, Metamask will connect to Ethereum's mainnet. To connect to our local "testnet," enable test networks for Metamask by clicking **Show/hide test networks**.
Next, click Metamask's network selector dropdown and click the **Add Network** button. Click **Add a network manually** and then provide the following information:
  * Network Name: `localhost`
  * New RPC URL: `http://127.0.0.1:8545`
  * Chain ID: `31337`
  * Currency Symbol: `ETH`

Add Localhost 8545 to Metamask
![](https://docs.arbitrum.io/img/apps-metamask-add-localhost-2025-01-13.png)
Your wallet won't have a balance on your local testnet's node, but you can import one of the test accounts into Metamask to access to 10,000 testnet `ETH`. Copy the private key of one of the test accounts (it works with or without the `0x` prefix, so e.g., `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80` or `ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`) and import it into Metamask. Metamask will ask you if you want to connect this new account to Remix, to which you should answer "yes":
![Connect Metamask to Localhost 8545](https://docs.arbitrum.io/img/apps-quickstart-import-metamask.png)
Your Ethereum Mainnet wallet's private key is the password to all of your tokens. Never share it with anyone; avoid copying it to your clipboard.
Note that in the context of this quickstart, "account" refers to an EOA (externally owned account), and its associated private key[5](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fn-5).
You should see a balance of 10,000 `ETH`. Keep your private key handy; we'll use it again shortly.
As we interact with our cupcake vending machine, we'll use Metamask's network selector dropdown to choose which network our cupcake transactions get sent to. We'll leave the network set to `Localhost 8545` for now.
#### Connect Remix to Metamask[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#connect-remix-to-metamask "Direct link to Connect Remix to Metamask")
In the last step, we'll connect Remix to Metamask so we can deploy our smart contract to the local chain using Remix.
Connect remix to Metamask
![](https://docs.arbitrum.io/img/apps-remix-connect-metamask-2025-01-13.gif)
At this point, we're ready to deploy our smart contract to any chain we want.
#### Deploy the smart contract to your local chain[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#deploy-the-smart-contract-to-your-local-chain "Direct link to Deploy the smart contract to your local chain")
  * In MetaMask, ensure that the `Localhost` network is selected.
  * In Remix, deploy the `VendingMachine` contract to the `Localhost` network, then go to the "Deploy & Run Transactions" tab and click "Deploy."

Deploy the VendingMachine contract to the Localhost network
![](https://docs.arbitrum.io/img/apps-remix-deploy-to-local-chain-2025-01-14.gif)
Then copy and paste your **contract address** below and click **Get cupcake!**. A prompt should ask you to sign a transaction that gives you a cupcake.
#### Free Cupcakes
web3-localhostMetamask wallet addressContract addressCupcake please!Refresh balance🧁
Cupcake balance:0 (no name)
### What's going on, here?[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#whats-going-on-here "Direct link to What's going on, here?")
Our first `VendingMachine` is labeled "Web2" because it demonstrates traditional client-server web application architecture: the back-end lives in a centralized network of servers.
![Architecture diagram](https://docs.arbitrum.io/img/apps-quickstart-vending-machine-architecture.png)
The "Web3" architecture is similar to the "Web2" architecture, with one key difference: with the "Web3" version, business logic and data are hosted by decentralized network of nodes**
Let's take a closer look at the differences between our `VendingMachine` implementations:
|  `WEB2`  
(the first one) |  `WEB3-LOCALHOST`  
(the latest one) |  `WEB3-ARB-SEPOLIA`  
(the next one) |  `WEB3-ARB-MAINNET`  
(the final one)  
---|---|---|---|---  
**Data** (cupcakes) | Stored only in your **browser**. (Usually, stored by centralized infrastructure.) | Stored on your **device** in an **emulated Ethereum network** (via smart contract). | Stored on Ethereum's **decentralized test network** (via smart contract). | Stored on Ethereum's **decentralized mainnet network** (via smart contract).  
**Logic** (vending) | Served from **Offchain's servers**. Executed by your **browser**. | Stored and executed by your **locally emulated Ethereum network** (via smart contract). | Stored and executed by Arbitrum's **decentralized test network** (via smart contract). | Stored and executed by Arbitrum's **decentralized mainnet network** (via smart contract).  
**Presentation** (UI) | Served from **Offchain's servers**. Rendered and executed by your **browser**. | ← same | ← same | ← same  
**Money** | Devs and users pay centralized service providers for server access using fiat currency. | ← same, but only for the presentation-layer concerns (code that supports frontend UI/UX). | ← same, but devs and users pay **testnet ETH** to testnet validators. | ← same, but instead of testnet `ETH`, they use **mainnet`ETH`**.  
So far, we've deployed our "Web3" app to an emulated blockchain (Anvil), which is a normal step in EVM development.
Next, we'll deploy our smart contract to a network of real nodes: Arbitrum's Sepolia testnet.
### Deploy the smart contract to the Arbitrum Sepolia testnet[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#deploy-the-smart-contract-to-the-arbitrum-sepolia-testnet "Direct link to Deploy the smart contract to the Arbitrum Sepolia testnet")
We were able to deploy to a testnet for free because we were using Remix's built-in network, but now we'll deploy our contract to Arbitrum's Sepolia testnet. Sepolia is powered by a network of nodes ran across the world by various participants, we'll need to compensate them with a small transaction fee in order to deploy our smart contract.
To be able to pay the transaction fee, we will:
  * Use our MetaMask crypto wallet
  * Obtain some Arbitrum Sepolia testnet's token called `ETH`.


Click Metamask's **Network selector** dropdown, and then click the **Add Network** button. Click **Add a network manually** and then provide the following information:
  * Network Name: `Arbitrum Sepolia`
  * New RPC URL: `https://sepolia-rollup.arbitrum.io/rpc`
  * Chain ID: `421614`
  * Currency Symbol: `ETH`


As we interact with the cupcake vending machine, we'll use Metamask's network selector dropdown to determine which network our cupcake transactions are sent to.
Next, let's deposit some `ETH` into the wallet corresponding to the private key we added to Remix. At the time of this quickstart's writing, the easiest way to acquire `ETH` is to bridge Sepolia `ETH` from Ethereum's parent chain Sepolia network to Arbitrum's child chain Sepolia network:
  1. Use a parent chain Sepolia `ETH` faucet like `ETH` on parent chain Sepolia.
  2. Bridge your parent chain Sepolia `ETH` into Arbitrum child chain using [the Arbitrum bridge](https://bridge.arbitrum.io/).


Once you've acquired some `ETH`, you'll be able to deploy your smart contract to Arbitrum's Sepolia testnet. You can proceed exactly as with the local testnet.
  1. Connect Remix to the Arbitrum Sepolia testnet
  2. Compile your vending machine contract
  3. Deploy your vending machine contract to the Arbitrum Sepolia testnet


In this last step, your compiled smart contract will be deployed through the RPC endpoint corresponding to "Arbitrum Sepolia" in MetaMask (MetaMask uses 
Congratulations! You've just deployed **business logic and data** to Arbitrum Sepolia. This logic and data will be hashed and submitted within a transaction to Ethereum's parent chian Sepolia network, and then it will be mirrored across all nodes in the Sepolia network[6](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fn-6).
To view your smart contract in a blockchain explorer, visit `https://sepolia.arbiscan.io/address/0x...B3`, but replace the `0x...B3` part of the URL with the full address of your deployed smart contract.
Select **Arbitrum Sepolia** from Metamask's dropdown, paste your contract address into the `VendingMachine` below, and click **Get cupcake!**. You should be prompted to sign a transaction that gives you a cupcake.
#### Free Cupcakes
web3-arb-sepoliaMetamask wallet addressContract addressCupcake please!Refresh balance🧁
Cupcake balance:0 (no name)
The final step is deploying our Cupcake machine to a production network, such as Ethereum, Arbitrum One, or Arbitrum Nitro. The good news is: deploying a smart contract in production is exactly the same as for Sepolia Testnet. The harder news: it will cost real money, this time. If you deploy on Ethereum, the fees can be significant and the transaction confirmation time 12 seconds on average. Arbitrum, a child chain, reduces these costs about 10X and a confirmation time in the same order while maintaining a similar level of security and decentralization.
### Summary[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#summary "Direct link to Summary")
In this quickstart, we:
  * Identified **two business rules** : 1) fair and permissionless cupcake distribution 2) immutable business logic and data.
  * Identified a **challenge** : These rules are difficult to follow in a centralized application.
  * Identified a **solution** : Using Arbitrum, we can decentralize business logic and data.
  * Converted a vending machine's Javascript business logic into a **Solidity smart contract**.
  * **Deployed our smart contract** to a local development network, and then Arbitrum's Sepolia testnet.


If you have any questions or feedback, reach out to us on **Request an update** button at the top of this page - we're listening!
### Learning resources[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#learning-resources "Direct link to Learning resources")
Resource | Description  
---|---  
| Official documentation for Solidity programming language  
| Learn Solidity patterns via a series of classic examples  
| Guide on upgrading Ethereum  
| Interactive smart contract hacking game  
| Rust programming course for blockchain development  
| Free online smart contract courses and tutorials  
| Web3 education platform with interactive lessons and projects  
| Web3 hackathon and project-based learning platform  
| Solidity bootcamp for beginners  
| Community-driven coding club with a focus on Web3 development  
| Metana is not mentioned in the resources, please provide more information about this resource.  
| Online education platform for blockchain and Web3 development courses  
## Footnotes[​](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#footnote-label "Direct link to Footnotes")
  1. The vending machine example was inspired by [↩](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fnref-1)
  2. Although application front-ends are usually hosted by centralized services, smart contracts allow the underlying logic and data to be partially or fully decentralized. These smart contracts are hosted and executed by Ethereum's public, decentralized network of nodes. Arbitrum has its own network of nodes that use advanced cryptography techniques to "batch process" Ethereum transactions and then submit them to the Ethereum parent chain, which significantly reduces the cost of using Ethereum. All without requiring developers to compromise on security or decentralization. [↩](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fnref-2)
  3. There are multiple types of Ethereum nodes. The ones that earn `ETH` for processing and validating transactions are called _validators_. See [↩](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fnref-3)
  4. When our `VendingMachine` contract is deployed to Ethereum, it'll be hosted by Ethereum's decentralized network of nodes. Generally speaking, we won't be able to modify the contract's code after it's deployed. [↩](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fnref-4)
  5. To learn more about how Ethereum wallets work, see [↩](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fnref-5)
  6. Visit the [Gentle Introduction to Arbitrum](https://docs.arbitrum.io/intro/) for a beginner-friendly introduction to Arbitrum's Rollup protocol. [↩](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#user-content-fnref-6)


Last updated on **Dec 9, 2025**
[ Next Estimate gas](https://docs.arbitrum.io/build-decentralized-apps/how-to-estimate-gas)
  * [What we'll learn](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#what-well-learn)
  * [Prerequisites](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#prerequisites)
  * [Ethereum and Arbitrum in a nutshell](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#ethereum-and-arbitrum-in-a-nutshell)
  * [Review the Javascript vending machine](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#review-the-javascript-vending-machine)
  * [Review the Solidity vending machine](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#review-the-solidity-vending-machine)
  * [Compile your smart contract with Remix](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#compile-your-smart-contract-with-remix)
  * [Deploy the smart contract to a local Ethereum chain](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#deploy-the-smart-contract-to-a-local-ethereum-chain)
  * [What's going on, here?](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#whats-going-on-here)
  * [Deploy the smart contract to the Arbitrum Sepolia testnet](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#deploy-the-smart-contract-to-the-arbitrum-sepolia-testnet)
  * [Summary](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#summary)
  * [Learning resources](https://docs.arbitrum.io/build-decentralized-apps/quickstart-solidity-remix#learning-resources)


  * [Arbitrum.io](https://arbitrum.io/)
  * [Arbitrum Rollup](https://arbitrum.io/rollup)
  * [Arbitrum AnyTrust](https://arbitrum.io/anytrust)
  * [Arbitrum Orbit](https://arbitrum.io/orbit)
  * [Arbitrum Stylus](https://arbitrum.io/stylus)
  * [Arbitrum whitepaper](https://docs.arbitrum.io/nitro-whitepaper.pdf)


  * [Network status](https://status.arbitrum.io/)
  * [Portal](https://portal.arbitrum.io/)
  * [Bridge](https://bridge.arbitrum.io/)
  * [Support](https://support.arbitrum.io/)


  * [Research forum](https://research.arbitrum.io/)
  * [Privacy Policy](https://arbitrum.io/privacy)
  * [Terms of Service](https://arbitrum.io/tos)


© 2025 Offchain Labs
![](https://cdn.usefathom.com/?h=https%3A%2F%2Fdocs.arbitrum.io&p=%2Fbuild-decentralized-apps%2Fquickstart-solidity-remix&r=&sid=DOHOZGJO&qs=%7B%7D&cid=56877415)

