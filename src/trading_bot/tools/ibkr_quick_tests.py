import sys
from ib_insync import *

HOST = '127.0.0.1'
PORT = 7497  # IB Gateway Paper
CLIENT_ID = 1


def connect_ib() -> IB:
    ib = IB()
    ib.connect(host=HOST, port=PORT, clientId=CLIENT_ID)
    return ib


def test_connect():
    ib = connect_ib()
    print({'Connected': ib.isConnected(), 'Accounts': ib.managedAccounts()})
    ib.disconnect()


def test_market_data():
    ib = connect_ib()
    # MES front-month contract; adjust month if needed
    contract = Future(symbol='MES', exchange='CME', currency='USD', lastTradeDateOrContractMonth='202503')
    ib.qualifyContracts(contract)
    ticker = ib.reqMktData(contract)
    ib.sleep(2)
    print({'Bid': ticker.bid, 'Ask': ticker.ask, 'Last': ticker.last})
    ib.cancelMktData(contract)
    ib.disconnect()


def test_order():
    ib = connect_ib()
    contract = Future(symbol='MES', exchange='CME', currency='USD', lastTradeDateOrContractMonth='202503')
    ib.qualifyContracts(contract)
    order = MarketOrder('BUY', 1)
    trade = ib.placeOrder(contract, order)
    ib.sleep(2)
    print({'OrderStatus': trade.orderStatus.status, 'Filled': trade.orderStatus.filled})
    ib.disconnect()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python ibkr_quick_tests.py [connect|market|order]')
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'connect':
        test_connect()
    elif cmd == 'market':
        test_market_data()
    elif cmd == 'order':
        test_order()
    else:
        print('Unknown command:', cmd)
        sys.exit(1)
