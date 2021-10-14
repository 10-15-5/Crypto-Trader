# Crypto-Trader README

This very simple program uses the CoinbasePro API and now the Binance API to buy a specific amount of crypto at a fixed time, (at time of 
writing I am just using the Windows Task Scheduler to make it run once a week) it then writes the detials of the 
purchase to a .log file and sends an email to tell me how much I have bought and at what price.

Uses the cbpro python client to interact with the Coinbase API.
Uses binance-python to interact with the Binance API.

## Getting Started

1) To set up the program go into settings/config and change the API codes, the email settings, 
   and the Currency you want to use.
2) After that the program will ask you what crypto you want to buy and how much you want to spend, 
   and these will be saved to a txt file in settings.

***You need to have funds in your respective account for this program to work***

*NB This program is not perfect and there may be a few bugs in it, just let me know if you find anything, and
I will try to fix it ASAP.*

*Some of this program does need to be changed to be more efficient, or to just use less code, I will be doing 
this soon I just haven't gotten around to it yet*
