import pytest
import random
import time
import yaml
from pathlib import Path
from brownie import exceptions, network
from web3 import Web3
from scripts.deploy_lottery import (
    deploy_lottery,
    enter_lottery,
    start_lottery,
    end_lottery,
)
from scripts.vrf_subscription import get_subscription
from scripts.utils import get_account, get_contract, LOCAL_BLOCKCHAIN_ENV


# ------------------  NOTES  ------------------
# Unit vs Integration test
# 1. Unit:  test each function on an isolated environment -> usually on development
#           added the script to tests/unit/
# 2. Integration:   test the complex integration between function -> usually on testnet
#                   added the script to tests/integration/
# ---------------------------------------------


def test_get_entrance_fee():
    """
    To test the entrance fee calculation and precision

    Notes
    -----
    Only applies to local chain, since this is a unit test
    """
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Unit test get entrance fee is for LOCAL testing only!")
    # Arrange
    lottery = deploy_lottery()
    # Act
    entrance_fee = lottery.getEntranceFee()
    expected_fee = Web3.toWei(0.025, "ether") + 1
    # Assert
    assert entrance_fee == expected_fee


def test_cant_enter_unless_started():
    """Unit test to ensure entering a lottery before starting it should not be allowed."""
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Unit test enter lottery is for LOCAL testing only!")
    # Arrange
    deploy_lottery()
    # Act and Assert
    with pytest.raises(exceptions.VirtualMachineError):
        enter_lottery()


def test_can_start_and_enter_lottery():
    """Unit test to ensure entering lottery is available after starting the lottery."""
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Unit test start/enter lottery is for LOCAL testing only!")
    # Arrange
    account = get_account()
    lottery = deploy_lottery()
    # Act
    start_lottery()
    enter_lottery()
    # Assert
    assert lottery.players(0) == account


def test_can_end_lottery():
    """Unit test to end the lottery."""
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Unit test end lottery is for LOCAL testing only!")
    # Arrange
    lottery = deploy_lottery()
    start_lottery()
    enter_lottery()
    # Act
    end_lottery(is_wait=False)
    # Arrange: status should be CALCULATING_WINNER because no Chainlink Oracle to fulfill
    assert lottery.lotteryState() == 2


def test_can_pick_winner_correctly():
    """Unit test for the contract to pick the winner."""
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Unit test to pick the lottery winner is for LOCAL testing only!")
    # Arrange 1: init params
    account = get_account()
    vrf_coordinator = get_contract("vrf_coordinator")
    lottery = deploy_lottery()
    lottery_balance_init = lottery.balance()
    print(f"Starting lottery balance: {lottery_balance_init}")
    start_lottery()
    # Arrange 2: winning condition
    num_players = random.randint(3, 5)  # random number from 3 to 5
    winning_rng = random.randint(100, 100000)  # random number from 100 to 100,000
    winning_index = int(winning_rng % num_players)
    print(
        f"Number of players: {num_players}, winning RNG: {winning_rng} "
        f"and winning index: {winning_index}"
    )

    # Act 1: enter the lottery
    for i in range(num_players):  # add with multiple different players
        enter_lottery(player_account=get_account(index=i))
    end_tx = lottery.endLottery({"from": account})
    request_id = end_tx.events["RequestEnd"]["requestId"]  # get ID from tx Event!
    print(f"Get request ID from the RequestEnd event: {request_id}")
    # Act 2: pick the lottery winner
    expected_winner = get_account(index=winning_index)
    winner_balance_before = expected_winner.balance()
    lottery_balance = lottery.balance()
    # Act 3: handle the VRF coordinator callback / fulfill
    fulfill_tx = vrf_coordinator.fulfillRandomWordsWithOverride(
        request_id, lottery.address, [winning_rng], {"from": account}
    )
    fulfill_tx.wait(1)
    winner_balance_after = expected_winner.balance()

    # Assert
    assert lottery.recentWinner() == expected_winner
    print(f"Expected: {expected_winner} vs Picked: {lottery.recentWinner()}")
    assert winner_balance_after == winner_balance_before + lottery_balance
    print(f"Winner balance: {winner_balance_before} vs after: {winner_balance_after}")
    assert lottery.balance() == lottery_balance_init
    print(f"Final lottery balance: {lottery.balance()}")


def test_create_new_subscription():
    """Unit test for obtaining a newly generated VRF subscription."""
    if network.show_active() in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Unit test to create subscription is NOT for PERSISTENT chain!")
    # Arrange
    network_id = network.show_active()
    account = get_account()
    sub_id = get_subscription(is_create_new=True)
    vrf_coordinator = get_contract("vrf_coordinator")
    # Act
    time.sleep(30)  # wait for the subscription transaction(s)
    brownie_config_path = Path("brownie-config.yaml").absolute()
    sub_balance, _, _, _ = vrf_coordinator.getSubscription(sub_id)
    # Assert
    with open(brownie_config_path, "r") as file:
        brownie_config = yaml.safe_load(file)
        assert brownie_config["networks"][network_id]["subscription_id"] == sub_id
        assert brownie_config["networks"][network_id]["fund_amount"] == sub_balance
    # Clean up (cancelling the test subscription)
    cancel_tx = vrf_coordinator.cancelSubscription(sub_id, account, {"from": account})
    cancel_tx.wait(1)
