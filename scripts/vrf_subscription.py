import yaml
from typing import Union, Optional
from pathlib import Path
from brownie import config, network, convert
from .utils import LOCAL_BLOCKCHAIN_ENV, get_account, get_contract


def get_subscription(is_create_new: bool = False) -> int:
    """
    To get the VRF subscription ID if a subscription exists, if not:
    1. Create a new subscription.
    2. Fund the subscription.
    3. Get the subscription ID.

    Parameters
    ----------
    is_create_new: `bool`
        Forcefully create a new subscription, and overwrite the existing config.

    Returns
    -------
    `int`: The subscription ID.
    """
    # get the VRF coordinator
    network_id = network.show_active()
    account = get_account()
    vrf_coordinator = get_contract(contract_name="vrf_coordinator")

    # create a new subscription if it's not yet available
    sub_id = config["networks"].get(network_id, {}).get("subscription_id")
    if sub_id is None or is_create_new:
        print(f"Creating a new subscription ... ")
        create_sub = vrf_coordinator.createSubscription({"from": account})
        create_sub.wait(1)
        # obtain the newly generated subscription ID
        sub_id = create_sub.events[0]["subId"]
        print(f"Obtained a new Subscription ID: {sub_id} !")
        # store the ID for further usage (only if not on LOCAL chain!)
        if network_id not in LOCAL_BLOCKCHAIN_ENV:
            brownie_config_path = Path("brownie-config.yaml").absolute()
            with open(brownie_config_path, "r") as file:
                brownie_config = yaml.safe_load(file)
                brownie_config["networks"][network_id]["subscription_id"] = int(sub_id)
            with open(brownie_config_path, "w") as file:
                yaml.dump(brownie_config, file)
            print(f"New subscription ID ({sub_id}) for {network_id} is saved!")
    else:
        print(f"A VRF subscription already exists: {sub_id}!")

    # check if the subscription has sufficient fund!
    if not is_subscription_funded(subscription_id=sub_id):
        print(f"The subscription {sub_id} has INSUFFICIENT fund!")
        fund_subscription(subscription_id=sub_id)
    return sub_id


def is_subscription_funded(subscription_id: int) -> bool:
    """
    To check if the subscription has sufficient fund.

    Parameters
    ----------
    subscription_id: `int`
        The subscription ID
    """
    vrf_coordinator = get_contract(contract_name="vrf_coordinator")
    sub_details = vrf_coordinator.getSubscription(subscription_id)
    print(f"Subscription {subscription_id} details: {sub_details}")
    # check if the subscription balance has sufficient fund
    minimum_fund = config["networks"][network.show_active()].get("fund_amount", 0)
    return sub_details[0] > minimum_fund


def fund_subscription(
    subscription_id: int, link_amount: Union[int, float, None] = None
):
    """
    To fund the subscription.

    Parameters
    ----------
    subscription_id: `int`
        The subscription ID
    link_amount: `Union[int, float, None]`
        The LINK token amount to fund the subscription, without precision.
    """
    # init params
    network_id = network.show_active()
    account = get_account()
    if link_amount is None:
        fund_amount = config["networks"][network_id]["fund_amount"]
    else:
        fund_amount = int(link_amount * (10**18))  # 18 precision
    vrf_coordinator = get_contract(contract_name="vrf_coordinator")
    # handle funding for LOCAL chain or not
    print(f"Begin funding {link_amount} LINK to Subscription {subscription_id} ... ")
    if network_id in LOCAL_BLOCKCHAIN_ENV:
        fund_sub = vrf_coordinator.fundSubscription(
            subscription_id, fund_amount, {"from": account}
        )
        fund_sub.wait(1)
    else:  # wallet transfer the LINK token
        link_token = get_contract("link_token")
        fund_sub = link_token.transferAndCall(
            vrf_coordinator.address,
            fund_amount,
            convert.to_bytes(subscription_id),
            {"from": account},
        )
        fund_sub.wait(1)
    # get the latest subscription balance
    sub_balance, _, _, _ = vrf_coordinator.getSubscription(subscription_id)
    sub_balance_precision = sub_balance / (10**18)
    print(
        f"Successfully funded the subscription: {subscription_id}! "
        f"Current subscription balance: {round(sub_balance_precision, 2)} LINK."
    )


def register_consumer(contract_address: str, subscription_id: Optional[int] = None):
    """
    To check if an address is already registered as a consumer, will register it
    if it's not yet a consumer.

    Parameters
    ----------
    contract_address: `str`
        The contract address to check.
    subscription_id: `Optional[int]`
        The subscription ID.
    """
    account = get_account()
    vrf_coordinator = get_contract(contract_name="vrf_coordinator")
    if subscription_id is None:
        subscription_id = config["networks"][network.show_active()]["subscription_id"]
    # get the subscription details
    try:
        _, _, _, sub_consumers = vrf_coordinator.getSubscription(subscription_id)
    except Exception as e:
        print(
            f"The subscription {subscription_id} is NOT available in the "
            f"VRF coordinator! Please check again!"
        )
        raise e
    print(f"Available consumers of {subscription_id} are: {sub_consumers}")
    # registering the consumer if not yet available
    if contract_address in sub_consumers:
        print(
            f"The smart contract '{contract_address}' is already registered "
            f"as a consumer in subscription {subscription_id}!"
        )
    else:
        print(f"Registering {contract_address} as a consumer in {subscription_id} ... ")
        add_consumer = vrf_coordinator.addConsumer.transact(
            subscription_id, contract_address, {"from": account}
        )
        add_consumer.wait(1)


def main():
    # sub_id = config["networks"][network.show_active()]["subscription_id"]
    # fund_subscription(subscription_id=sub_id, link_amount=4)
    print(f"Get subscription: {get_subscription()}")
    # register_consumer("0xef0520a5bf13ca3485f2cc2720a6118dc8a52613", 2995)
