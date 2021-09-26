import cbpro
import os
import logging
import time
import configparser
import sys
import smtplib
import math

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance.enums import *

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------------------------------------------------------
#   Logging Setup
# ------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(message)s')

file_handler = logging.FileHandler("settings\\logs.log", encoding='utf8')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# ------------------------------------------------------------------

config = configparser.RawConfigParser()
configFilePath = r"settings/config.txt"
config.read(configFilePath, encoding="utf-8")


# Global variables
auth_client = cbpro.AuthenticatedClient(config.get("CONFIG", "CB_PRO_PUBLIC"),
                                        config.get("CONFIG", "CB_PRO_PRIVATE"),
                                        config.get("CONFIG", "CB_PRO_PASSPHRASE")
                                        )
public_client = cbpro.PublicClient()

binance_client = Client(config.get("CONFIG", "BINANCE_PUBLIC_KEY"),
                        config.get("CONFIG", "BINANCE_PRIVATE_KEY")
                        )


def getcoins():
    print("Please enter the symbol of the coins you want to buy (if buying multiple, seperate them with commas):")
    coins = input().upper()
    coins = coins.replace(" ", "")
    coins = coins.split(",")
    for i in range(len(coins)):
        # Check to see if coin can be bought on CoinbasePro
        pair = coins[i] + "-" + config.get("CONFIG", "COINBASE_CURRENCY")
        response = public_client.get_product_order_book(pair)

        if "message" in response:
            try:
                binance_client.get_order_book(symbol=coins[i] + config.get("CONFIG", "BINANCE_CURRENCY"))
                coins[i] += "-BINANCE"
            except:
                print(pair + " is an invalid trading pair for CoinbasePro & Binance, "
                             "please re-run the program and try again")
                sys.exit()
        else:
            coins[i] += "-COINBASE"

    getpurchaseamount(coins)


def getpurchaseamount(coins):
    amount = []
    # currency = config.get("CONFIG", "CURRENCY")
    # print("How much do you want to spend? (Minimum amount per transaction is 10" + currency + ")")
    for i in range(len(coins)):
        market = coins[i].split("-")[1]
        if market == "COINBASE":
            currency = config.get("CONFIG", "COINBASE_CURRENCY")
            print("How much do you want to spend? (Minimum amount per transaction is €10)")
        else:
            currency = config.get("CONFIG", "BINANCE_CURRENCY")
            print("How much do you want to spend? (Minimum amount per transaction is €10)")
        next_coin = False
        while not next_coin:
            spend = input(coins[i] + ":\t" + currency)
            try:
                spend = float(spend)
                amount.append(str(spend))
                if spend < 10:
                    print("Has to be more than 10, Try again!")
                else:
                    next_coin = True
            except ValueError:
                print("Please only enter digits, Try again!")

    with open("settings/coins.txt", "w") as file:
        for i in range(len(coins)):
            value_to_write = f'{coins[i]}-{amount[i]}\n'
            file.write(value_to_write)


def buycrypto(specs):

    if specs["market"] == "Coinbase":
        order = auth_client.buy(order_type="market",
                                product_id=specs["coin"] + "-" + config.get("CONFIG", "CURRENCY"),
                                funds=specs["amount"])  # Amount you want to buy

        order_id = order["id"]  # Uses the order ID to get specific details of transaction

        time.sleep(10)  # Wait 10 seconds for CB to catch up and log all the transactions

    else:
        try:

            coin_price = float(binance_client.get_symbol_ticker(
                symbol=specs["coin"] + config.get("CONFIG", "BINANCE_CURRENCY")
            )["price"])

            quantity_floor = round_decimals_down((float(specs["amount"]) / coin_price), 6)

            # Binance API won't let you buy in fractions if the coin costs less than $1
            if quantity_floor > 1:
                quantity_floor = math.floor(quantity_floor)

            order = binance_client.create_order(
                symbol=specs["coin"] + config.get("CONFIG", "BINANCE_CURRENCY"),
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity_floor,
                )

            order_id = order["orderId"]
        except BinanceAPIException as e:
            print(e.status_code)
            print(e.message)
        except BinanceOrderException as e:
            print(e)

    return order_id


def round_decimals_down(number:float, decimals:int=2):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor


def writetolog(dets, market):
    if market == "COINBASE":
        try:
            msg = f'{dets["product_id"]} - Date & Time:{dets["created_at"]} - Gross Spent: {dets["specified_funds"]}' \
                f' - Fees: {dets["fill_fees"]} - Net Spent: {dets["funds"]}' \
                f' - Amount Bought: {dets["filled_size"]}'
        except:
            msg = "Error getting order details from Coinbase"  # Don't want to break the whole program so it prints this instead
    else:
        created_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(dets["time"]))
        try:
            msg = f'{dets["symbol"]} - Date & Time:{created_at} - Gross Spent: {dets["price"]}' \
                f' - Amount Bought: {dets["origQty"]}'
        except:
            msg = "Error getting order details from Binance"  # Don't want to break the whole program so it prints this instead
    

    logger.info(msg)


def sendemail(order_details, market):
    smtp = smtplib.SMTP(config.get('CONFIG', 'SMTP_SERVER'), int(config.get('CONFIG', 'SMTP_PORT')))
    smtp.ehlo()
    smtp.starttls()

    smtp.login(config.get('CONFIG', 'SMTP_SENDING_EMAIL'), config.get('CONFIG', 'SMTP_PASSWORD'))

    if market == "COINBASE":
        try:
            text = f'{order_details["product_id"]} - You got {order_details["filled_size"]} for ' \
                f'{config.get("CONFIG", "CURRENCY")}{float(order_details["specified_funds"]): .2f}'
        except:
            text = f'You bought some crypto but for some reason the messaging part of it fucked up!'
    else:
        try:
            text = f'{order_details["symbol"]} - You got {order_details["executedQty"]} for ' \
                f'{config.get("CONFIG", "CURRENCY")}{float(order_details["price"]): .2f}'
        except:
            text = f'You bought some crypto but for some reason the messaging part of it fucked up!'

    subject = "DCA Weekly Notification"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg.attach(MIMEText(text))

    smtp.sendmail(
        from_addr=config.get('CONFIG', 'SMTP_SENDING_EMAIL'),
        to_addrs=config.get('CONFIG', 'SMTP_RECEIVING_EMAIL'),
        msg=msg.as_string()
    )
    smtp.quit()


def main():
    if not os.path.isfile("settings/coins.txt"):
        getcoins()

    order_ids = {}
    with open("settings/coins.txt", "r") as coins:
        coin_and_amount = coins.read().splitlines()
        for i in range(len(coin_and_amount)):
            split = coin_and_amount[i].split("-")
            specs = {"coin": split[0], "market": split[1], "amount": split[2]}
            order_ids.update({
                "market": specs["market"],
                "order id": buycrypto(specs),
                "coin paring": split[0],
            })

    for x in order_ids:
        if x["market"] == "COINBASE":
            # Uses the order ID to get specific details of transaction
            dets = auth_client.get_order(x["order id"])
        else:
            dets = binance_client.get_order(symbol=x["coin pairing"], orderId=x["order id"])
        writetolog(dets, x["market"])
        sendemail(dets, x["market"])


if __name__ == '__main__':
    main()
