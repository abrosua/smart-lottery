# Smart Lottery
A decentralized lottery smart contract built with Brownie and OpenZeppelin. Deployed on [Sepolia Testnet](https://sepolia.dev/).

This project is inspired by the [smartcontract-lottery](https://github.com/PatrickAlphaC/smartcontract-lottery) by [freeCodeCamp](https://www.youtube.com/watch?v=M576WGiDBdQ&list=PLzRreXG8NJkK0Vuvh-cbx6KJy8t8ml2OG&index=37) using the [VRF V2 Subscription Method](https://docs.chain.link/vrf/v2/subscription).

How the lottery works?
1. Admin will start the lottery.
2. Users can enter lottery as a player by paying a certain amount of ETH, based on a USD entrance fee.
3. The admin will then close/end the lottery manually.
4. The lottery will then randomly select the winner and the total entrance funds will be automatically transferred to the winner's address.