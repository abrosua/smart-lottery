// SPDX-License-Identifier: MIT
pragma solidity ^0.8.5;
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@chainlink/contracts/src/v0.8/interfaces/VRFCoordinatorV2Interface.sol";
import "@chainlink/contracts/src/v0.8/VRFConsumerBaseV2.sol";

// inherit OpenZeppelin's Ownable contract!
contract Lottery is VRFConsumerBaseV2, Ownable {
    // event
    event RequestEnd(uint256 requestId, uint32 numWords);
    event RequestFulfilled(uint256 requestId, uint256[] randomWords);

    // init variables
    address payable[] public players;
    address payable public recentWinner;
    uint256 public randomness;
    uint256 public usdEntryFee;
    AggregatorV3Interface internal _dataFeed; // start with _ for private variable
    VRFCoordinatorV2Interface internal _coordinator;

    // VRF variables
    uint64 public immutable subscriptionId;
    bytes32 public immutable keyHash;
    uint256 public requestId;
    uint32 _callbackGasLimit = 100000;
    uint16 _minRequestConfirmations = 3; // The default is 3, but you can set this higher.
    uint32 _numWords = 1; // number of random words to retrieve

    // Create enum to define the current lottery state
    enum LotteryState {
        OPEN, // idx 0
        CLOSED, // idx 1
        CALCULATING_WINNER // idx 2
    }
    LotteryState public lotteryState;

    constructor(
        address _dataFeedAddress,
        address _coordinatorAddress,
        uint64 _subscriptionId,
        bytes32 _keyHash
    ) VRFConsumerBaseV2(_coordinatorAddress) {
        // init. chainlink price feed (dynamic data feed address)
        _dataFeed = AggregatorV3Interface(_dataFeedAddress);
        usdEntryFee = 50 * (10 ** 18);
        lotteryState = LotteryState.CLOSED;
        // init. the VRF coordinator and subscription ID
        // Sepholia Coordinator: 0x8103B0A8A00be2DDC778e6e7eaa21791Cd364625
        _coordinator = VRFCoordinatorV2Interface(_coordinatorAddress);
        subscriptionId = _subscriptionId;
        // Sepholia Key Hash: 0x474e34a077df58807dbe9c96d3c009b23b3c6d0cce433e59bbf5b34f823bc56c
        keyHash = _keyHash;
    }

    function enter() public payable {
        // check if the lottery state is currently OPEN
        require(lotteryState == LotteryState.OPEN, "The lottery is not open!");
        // check if the entrance fee is sufficient
        require(msg.value >= getEntranceFee(), "Insufficient fee!");
        // archive the player address
        players.push(payable(msg.sender));
    }

    function getEntranceFee() public view returns (uint256) {
        (, int answer, , , ) = _dataFeed.latestRoundData();
        uint256 price = uint256(answer * 10000000000);
        uint256 precision = 1 * 10 ** 18;
        return ((usdEntryFee * precision) / price) + 1;
    }

    // use OpenZeppelin inheritted ownership constructor!
    function startLottery() public onlyOwner {
        require(
            lotteryState == LotteryState.CLOSED,
            "Can't start a new lottery yet!"
        );
        lotteryState = LotteryState.OPEN;
    }

    function endLottery() public onlyOwner {
        // generating Random number in a deterministic system (blockchain) is impossible!
        // 1. Simple way: Pseudo Random numbers -> can be EXPLOITED! no PROD usage!
        // >>> Use the global variable (e.g., block difficulty and timestamp)
        /*
        uint256 numberRandomPseudo = uint256(
            keccak256( // hashing algorithm (consistent output)
                abi.encodePacked(
                    nonce, // predictable value
                    msg.sender, // predictable value
                    block.difficulty, // can be manipulated by miners! Vulnerable
                    block.timestamp // predictable value
                )
            )
        );
        uint256 indexRandomPseudo = numberRandomPseudo % players.length;
        */
        // 2. True Random Number: A proofable random number from Chainlink (oracle)
        // >>> Source: docs.chain.link/vrf/v2/subscription/examples/get-a-random-number
        lotteryState = LotteryState.CALCULATING_WINNER; // prevent asynchronous update
        requestId = _coordinator.requestRandomWords(
            keyHash,
            subscriptionId,
            _minRequestConfirmations,
            _callbackGasLimit,
            _numWords
        );
        // emit to event
        emit RequestEnd(requestId, _numWords);
    }

    // override the fulfill random callback
    function fulfillRandomWords(
        uint256 _requestId,
        uint256[] memory _randomWords
    ) internal override {
        /*
        require(s_requests[_requestId].exists, "request not found");
        s_requests[_requestId].fulfilled = true;
        s_requests[_requestId].randomWords = _randomWords;
        emit RequestFulfilled(_requestId, _randomWords);
        */
        require(
            lotteryState == LotteryState.CALCULATING_WINNER,
            "You are NOT there yet!"
        );
        require(_randomWords.length > 0, "Random words NOT found!");
        // pick the random winner
        uint256 indexOfWinner = _randomWords[0] % players.length;
        recentWinner = players[indexOfWinner];
        // transfer this contract balance to the winning address!
        recentWinner.transfer(address(this).balance);

        // reset the lottery
        players = new address payable[](0);
        lotteryState = LotteryState.CLOSED;
        randomness = _randomWords[0];
        // emit to event
        emit RequestFulfilled(_requestId, _randomWords);
    }
}
