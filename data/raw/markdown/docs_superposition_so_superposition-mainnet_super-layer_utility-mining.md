---
url: https://docs.superposition.so/superposition-mainnet/super-layer/utility-mining
title: Utility Mining | Superposition
category: orbit_sdk
subcategory: docs
scraped_at: 2025-12-20T10:42:09.221755
---

[![](https://docs.superposition.so/~gitbook/image?url=https%3A%2F%2F4196461559-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252FYG4cy6lsYDv5fGVs1u1l%252Ficon%252Flu3GN04cVH6Iw66IyUkY%252FROUNDED%2520EARS.png%3Falt%3Dmedia%26token%3Da03ac097-f7c2-4408-a5fb-89f3321092be&width=32&dpr=4&quality=100&sign=26c97299&sv=2)![](https://docs.superposition.so/~gitbook/image?url=https%3A%2F%2F4196461559-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252FYG4cy6lsYDv5fGVs1u1l%252Ficon%252Flu3GN04cVH6Iw66IyUkY%252FROUNDED%2520EARS.png%3Falt%3Dmedia%26token%3Da03ac097-f7c2-4408-a5fb-89f3321092be&width=32&dpr=4&quality=100&sign=26c97299&sv=2)Superposition](https://docs.superposition.so/)
`Ctrl``k`
  * [🔲Super Hub](https://docs.superposition.so/)
  * Introduction
    * [🐱Introducing Superposition](https://docs.superposition.so/introduction/introducing-superposition)
    * [📦Understanding Superposition](https://docs.superposition.so/introduction/understanding-superposition)
    * [🐾The Laws of Superposition](https://docs.superposition.so/introduction/the-laws-of-superposition)
    * [🛠️Roadmaps](https://docs.superposition.so/introduction/roadmaps)
  * 🐈Superposition Mainnet
    * [ℹ️ Mainnet Network Details](https://docs.superposition.so/superposition-mainnet/mainnet-network-details)
    * [🖥️ Using Superposition Mainnet](https://docs.superposition.so/superposition-mainnet/using-superposition-mainnet)
    * [🌉 Bridging to Superposition Mainnet](https://docs.superposition.so/superposition-mainnet/bridging-to-superposition-mainnet)
    * [🛤️Super Layer](https://docs.superposition.so/superposition-mainnet/super-layer)
      * [🪙Super Assets](https://docs.superposition.so/superposition-mainnet/super-layer/super-assets)
      * [💧Universal Shared Liquidity](https://docs.superposition.so/superposition-mainnet/super-layer/universal-shared-liquidity)
      * [⛏️Utility Mining](https://docs.superposition.so/superposition-mainnet/super-layer/utility-mining)
    * [👷Developers](https://docs.superposition.so/superposition-mainnet/developers)
    * [3️⃣Arbitrum Layer 3](https://docs.superposition.so/superposition-mainnet/arbitrum-layer-3)
  * ✨Native dApps
    * [🚰Faucet](https://docs.superposition.so/native-dapps/faucet)
    * [🔍Block Explorer](https://docs.superposition.so/native-dapps/block-explorer)
    * [🐈‍⬛Longtail AMM](https://docs.superposition.so/native-dapps/longtail-amm)
    * [](https://docs.superposition.so/native-dapps/9lives)
    * [📧Meow Domains](https://docs.superposition.so/native-dapps/meow-domains)
    * [🌈Bridge](https://docs.superposition.so/native-dapps/bridge)
  * Partnerships
    * [🤝Partnering with us](https://docs.superposition.so/partnerships/partnering-with-us)
    * [👐Join us](https://docs.superposition.so/partnerships/join-us)
  * Other Docs and Links
    * [🔗Official Links](https://docs.superposition.so/other-docs-and-links/official-links)
    * [🧑‍🤝‍🧑Community Hub](https://docs.superposition.so/other-docs-and-links/community-hub)


Copy
  1. [🐈Superposition Mainnet](https://docs.superposition.so/superposition-mainnet)
  2. [🛤️Super Layer](https://docs.superposition.so/superposition-mainnet/super-layer)


#  ⛏️Utility Mining
Utility mining is a mechanism that allows for the distribution of tokens based on user activity and active participation.
### 
[](https://docs.superposition.so/superposition-mainnet/super-layer/utility-mining#ispasted)
What Is Utility Mining?
Utility mining is a mechanism or process in which participants engage in protocol-specified on-chain activity and are rewarded with tokens for doing so. Protocols can utilize utility mining to distribute their native or governance tokens to end-users and attract new users to their protocols, helping bootstrap themselves as well as mitigating the risks of mercenary capital. This process incentivizes users to interact with the underlying protocol to receive additional yields. One of the risks of such a system is the potential for Sybil attacks, as yield is distributed on the basis of activity. One solution to this is leveraging the Transfer Rewards Function (TRF), allowing utility mining to sustainably distribute tokens in a probabilistic mechanism (the fact that rewards are distributed in tiers) each time any user performs an on-chain transaction. TRF is a custom mathematical function that distributes rewards through the use of assets. It takes into account the size of the rewards and the transaction count.
These rewards are distributed in tandem with other rewards, granting each network participant equal opportunities to generate large amounts of yield, whether they are sending or receiving these assets. For example, AMM A decides to distribute a portion of its tokens ($AMM) through utility mining. This may incentivize rational users of, for example, AMM B to use AMM A for a period of time to maximize their yield.
A user using AMM A will potentially be able to get exposure to AMM A tokens ($AMM) every time they make a trade, maximizing their expected outcome. However, to claim this yield, the user has to learn and understand how to use AMM A and be actively engaged in deriving utility out of it. The user may also be contributing towards its revenue for the services provided.
Once the yield towards the end of the utility mining initiative is reduced, the user may choose to remain a long-term user of AMM A, as they were able to derive value out of it and potentially keep using it for its value proposition.
### 
[](https://docs.superposition.so/superposition-mainnet/super-layer/utility-mining#why-utility-mining)
Why Utility Mining?
Traditional strategies of bootstrapping protocols, such as liquidity mining, are not working as intended. Protocols pay expensive fees to rent liquidity and receive little-to-no long-term benefits. Utility mining rewards users with governance tokens and other incentives, such as higher yield, when targeted on-chain interactions are made by a user. For example, performing a specific action in the protocol (swapping a certain pair, transacting a certain amount, etc.). This method rewards usage and active involvement in the network, ensuring that every participant receives the same value. This leads to a more even distribution of tokens across users, which lowers the entrance barrier for governance and creates a fair playing field.
By using utility mining, a fairer mechanism for the distribution of tokens incentivizing proactive participation in the protocol and broader ecosystem can be established. 
[PreviousLongtail Orderbook Specs](https://docs.superposition.so/superposition-mainnet/super-layer/universal-shared-liquidity/longtail-orderbook-specs)[NextDevelopers](https://docs.superposition.so/superposition-mainnet/developers)
Last updated 1 year ago
Was this helpful?
  * [What Is Utility Mining?](https://docs.superposition.so/superposition-mainnet/super-layer/utility-mining#ispasted)
  * [Why Utility Mining?](https://docs.superposition.so/superposition-mainnet/super-layer/utility-mining#why-utility-mining)


Was this helpful?

