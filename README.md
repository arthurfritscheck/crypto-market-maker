# Deribit Market Making Bot

An asynchronous, modular market making engine for Deribit perpetual futures. Built in Python using CCXT Pro WebSockets, it continuously quotes both sides of the order book and manages inventory risk through dynamic spread skewing.

---

## Architecture

The project is split into three modules with a clear separation of concerns:

```
main.py         # Execution engine — orchestrates the trading loop
strategy.py     # Quote calculation and inventory skew logic
database.py     # Non-blocking SQLite trade logging
```

### main.py — Execution Engine

The core event loop. Connects to Deribit via a persistent WebSocket and streams real-time ticker data using `watch_ticker()`. On each significant price move, it cancels stale orders, fetches the current position and account equity, requests fresh quotes from the strategy module, and places new limit orders on both sides.

A background async task runs concurrently every 30 seconds to fetch recent fills and log them to SQLite — completely decoupled from the trading loop so database I/O never introduces latency.

### strategy.py — Inventory Skew

Implements a classic inventory-aware market making strategy. The core idea: as the bot accumulates a directional position, it skews its bid and ask prices to encourage trades that flatten the book. A long inventory biases quotes lower to attract sellers; a short inventory biases quotes higher to attract buyers. This limits adverse selection and manages risk without manually unwinding positions.

### database.py — Trade Logging

Persists all fills to a local SQLite database, deduplicating by trade ID so repeated fetches don't create duplicate records. Runs as a non-blocking background task so it never stalls order placement.

---

## PnL Tracking

The engine tracks two PnL metrics in real-time on every market move:

- **Session PnL** — change in total account equity since the engine started, converted to USD
- **Open uPnL** — unrealized PnL on the current position, pulled directly from the exchange and converted to USD

---

## Planned Improvements/Roadmap

### Backtesting Framework
Replay historical order book data to simulate strategy performance offline. The goal is to tune spread width, skew aggressiveness, and inventory limits without risking capital — and to validate any changes before deploying them live.

### Avellaneda-Stoikov Inventory Skew
The current skew logic is linear and hand-tuned. A natural upgrade is the Avellaneda-Stoikov model, the academic foundation for inventory-aware market making. It derives optimal bid/ask offsets from closed-form equations based on current inventory, volatility, and a risk aversion parameter — giving the skew a more principled, dynamic basis.

### Order Book Imbalance (OBI)
Incorporate real-time order book imbalance as a directional signal. If the book is heavily weighted on the bid side, the price is more likely to move up — so quotes can be adjusted accordingly before inventory accumulates. This makes the bot more proactive rather than purely reactive.

### Volatility-Adjusted Spreads
Automatically widen quotes during high volatility to reduce adverse selection risk, and tighten them during calm periods to stay competitive. Could be driven by a rolling realized volatility estimate or implied volatility from Deribit's options market.

### Reconnection & Fault Tolerance
Currently if the WebSocket drops or an API call fails, the bot halts. A production-grade engine needs automatic reconnection, order state reconciliation on restart, and graceful handling of partial fills and stale orders.

### Multi-Symbol Support
Run the strategy concurrently across multiple instruments (e.g. BTC-PERPETUAL and ETH-PERPETUAL) within the same async event loop, sharing a single exchange connection.

### Parameter Optimization
Use the backtesting framework to run grid search or Bayesian optimization over key parameters — spread width, skew factor, max inventory, position size — to find configurations that maximize risk-adjusted returns.

---

## Stack

- **Python 3.11+**
- **CCXT Pro** — WebSocket market data and order management
- **asyncio** — concurrent execution without threads
- **SQLite** — lightweight local trade log
- **python-dotenv** — API key management