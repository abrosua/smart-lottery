import pytest
from brownie import network
from scripts.deploy_lottery import (
    deploy_lottery,
    enter_lottery,
    start_lottery,
    end_lottery,
)

from scripts.utils import get_account, LOCAL_BLOCKCHAIN_ENV


def test_can_pick_winner():
    """Integration test for the contract to pick the winner."""
    if network.show_active() in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Integration test to pick the winner is NOT for PERSISTENT chain!")
    # Arrange
    account = get_account()
    lottery = deploy_lottery()
    start_lottery()
    enter_lottery()
    # Act
    end_lottery()
    # Assert
    assert lottery.recentWinner() == account
    assert lottery.balance() == 0
    assert lottery.randomness() > 0
    print(f"The winning RNG: {lottery.randomness()}")
