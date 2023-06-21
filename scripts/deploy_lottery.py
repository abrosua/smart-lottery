import time
from typing import Optional
from brownie import Lottery, config, network
from .utils import get_account, get_contract
from .vrf_subscription import get_subscription, register_consumer


def deploy_lottery():
    network_id = network.show_active()
    account = get_account()
    # get the VRF subscription ID
    subscription_id = get_subscription()
    # 30 gwei Key Hash: https://docs.chain.link/vrf/v2/subscription/supported-networks
    key_hash = config["networks"][network_id]["key_hash"]  # aka Gas Lane

    # deploy the Lottery contract here
    lottery = Lottery.deploy(
        get_contract(contract_name="eth_usd_price_feed").address,
        get_contract(contract_name="vrf_coordinator").address,
        subscription_id,
        key_hash,
        {"from": account},
        publish_source=config["networks"].get(network_id, {}).get("verify", False),
    )

    # register the deployed contract to the VRF subscription
    register_consumer(contract_address=lottery.address, subscription_id=subscription_id)
    return lottery


def start_lottery():
    """To start the lottery."""
    account = get_account()
    lottery = Lottery[-1]
    print(f"Starting the lottery ... Status: '{lottery.lotteryState()}'")
    start_tx = lottery.startLottery({"from": account})
    start_tx.wait(1)
    print(f"The lottery is officially started! Status: '{lottery.lotteryState()}'")


def enter_lottery(player_account: Optional[str] = None):
    """To enter the lottery."""
    if player_account is None:
        player_account = get_account()
    lottery = Lottery[-1]
    entrance_fee = lottery.getEntranceFee() + (10**8)
    # enter the lottery
    enter_tx = lottery.enter({"from": player_account, "value": entrance_fee})
    enter_tx.wait(1)
    print(f"Successfully entered the lottery! Player address: {player_account}")


def end_lottery(is_wait: bool = True):
    """To end the lottery and find the winner!"""
    account = get_account()
    lottery = Lottery[-1]
    end_tx = lottery.endLottery({"from": account})
    end_tx.wait(1)
    # wait for the VRF fulfill
    if is_wait:
        time.sleep(60)
    winner_address = lottery.recentWinner()
    print(
        f"The lottery has officially ended! Status: '{lottery.lotteryState()}'. "
        f"The winner is: '{winner_address}' with randomness: '{lottery.randomness()}'"
    )


def main():
    deploy_lottery()
    start_lottery()
    enter_lottery()
    end_lottery()
