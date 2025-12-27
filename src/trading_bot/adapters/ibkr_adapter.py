from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

from trading_bot.broker_gateway.ibkr.connection_manager import IBKRConnectionManager
from trading_bot.broker_gateway.ibkr.execution_adapter import intent_to_ibkr_orders
from trading_bot.broker_gateway.ibkr.account_adapter import AccountAdapter
from trading_bot.broker_gateway.ibkr.session_manager import SessionManager
from trading_bot.broker_gateway.ibkr.orders_monitor import OrdersMonitor
from trading_bot.broker_gateway.ibkr.market_data_manager import MarketDataManager
from trading_bot.broker_gateway.ibkr.constitutional_filter import filter_order_intent, ConstitutionalState, Constitution

@dataclass
class IBKRAdapter:
    mode: str = "OBSERVE"  # OBSERVE | LIVE
    host: str = "127.0.0.1"
    port: int = 7497  # Paper
    client_id: int = 1
    
    # Internal state
    conn: IBKRConnectionManager = field(default_factory=IBKRConnectionManager)
    account: AccountAdapter = field(default_factory=AccountAdapter)
    session: SessionManager = field(default_factory=SessionManager)
    orders_monitor: OrdersMonitor = field(default_factory=OrdersMonitor)
    market_data: MarketDataManager = field(default_factory=MarketDataManager)
    killed: bool = False
    execution_enabled: bool = False
    _data_mode: Optional[int] = None
    
    _ib: Any | None = None
    _mes_contract: Any | None = None
    _open_orders: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _events: List[Dict[str, Any]] = field(default_factory=list)
    _idempotent_orders: Dict[str, str] = field(default_factory=dict)  # intent_id -> broker_order_id
    _bar_buffer: List[Dict[str, Any]] = field(default_factory=list)  # For bar callbacks

    def _ensure_connection(self) -> bool:
        """Ensure LIVE connection is established."""
        if self.mode != "LIVE":
            return True
        if self._ib:
            return True
        try:
            import ib_insync as ibis
            self._ib = ibis.IB()
            self._ib.connect(self.host, self.port, clientId=self.client_id)
            # Define MES contract deterministically (avoid ambiguity)
            self._mes_contract = self._resolve_primary_contract()
            self._ib.qualifyContracts(self._mes_contract)
            
            # Wire adapters
            self.conn._ib = self._ib
            self.account.set_connection(self._ib)
            self.orders_monitor.set_connection(self._ib, self._mes_contract)
            self.market_data.set_connection(self._ib, self._mes_contract)
            
            # Subscribe to order/fill events
            self.orders_monitor.subscribe(
                on_order_update=self._on_order_update,
                on_fill_update=self._on_fill_update
            )
            
            # Subscribe to market data
            self.market_data.subscribe(on_bar=self._on_bar)
            
            self.conn.state = "CONNECTED"
            self.conn.last_heartbeat = datetime.utcnow()
            return True
        except Exception as e:
            self._ib = None
            self._events.append({"type": "CONNECTION_ERROR", "error": str(e)})
            return False

    def _on_bar(self, bar: Dict[str, Any]) -> None:
        """Handle new 1-min bar from market data manager."""
        self._bar_buffer.append(bar)
        if len(self._bar_buffer) > 100:
            self._bar_buffer.pop(0)
        self._events.append({"type": "MARKET_BAR", **bar})

    def _on_order_update(self, ev: Dict[str, Any]) -> None:
        """Handle order status updates from monitor."""
        self._events.append({"type": "ORDER_STATUS_UPDATE", **ev})

    def _on_fill_update(self, ev: Dict[str, Any]) -> None:
        """Handle fill updates from monitor."""
        self._events.append({"type": "FILL_UPDATE", **ev})

    def set_kill_switch(self, on: bool) -> None:
        self.killed = bool(on)
        if self.killed:
            self._events.append({"type": "KILL_SWITCH_ACTIVATED"})

    class ExecutionNotAllowedError(Exception):
        pass

    def enable_execution(self, enabled: bool = True) -> None:
        self.execution_enabled = bool(enabled)
        self._events.append({"type": "EXECUTION_ENABLED_SET", "enabled": self.execution_enabled})

    def assert_execution_allowed(self, now: Optional[datetime] = None, reason_context: Optional[Dict[str, Any]] = None) -> None:
        ts = now or datetime.utcnow()
        ctx = reason_context or {}
        if self.killed:
            self._events.append({"type": "EXECUTION_BLOCKED", "reason": "KILL_SWITCH", "context": ctx})
            raise IBKRAdapter.ExecutionNotAllowedError("Kill switch active")
        # Account readiness gate: require non-zero net liquidation
        try:
            acct = self.get_account_snapshot() or {}
            raw = acct.get("raw") or {}
            account_ready = "NetLiquidation" in raw or acct.get("equity") is not None
            capital_ready = float(acct.get("equity", 0.0) or 0.0) > 0.0
            if not account_ready:
                self._events.append({"type": "EXECUTION_BLOCKED", "reason": "ACCOUNT_DATA_MISSING", "context": ctx})
                raise IBKRAdapter.ExecutionNotAllowedError("Account data missing")
            if not capital_ready:
                self._events.append({"type": "EXECUTION_BLOCKED", "reason": "ACCOUNT_NOT_READY", "context": ctx})
                raise IBKRAdapter.ExecutionNotAllowedError("Account not ready")
        except IBKRAdapter.ExecutionNotAllowedError:
            raise
        except Exception:
            self._events.append({"type": "EXECUTION_BLOCKED", "reason": "ACCOUNT_DATA_MISSING", "context": ctx})
            raise IBKRAdapter.ExecutionNotAllowedError("Account data missing")
        if not self.execution_enabled:
            self._events.append({"type": "EXECUTION_BLOCKED", "reason": "EXECUTION_DISABLED", "context": ctx})
            raise IBKRAdapter.ExecutionNotAllowedError("Execution disabled")
        if not self.is_session_open(now=ts):
            self._events.append({"type": "EXECUTION_BLOCKED", "reason": "MARKET_CLOSED", "context": ctx})
            raise IBKRAdapter.ExecutionNotAllowedError("Market closed")

    # --- Utility helpers for weekend posture and data mode ---
    def set_data_mode(self, mode: int = 4) -> None:
        """Set market data mode: 1=RealTime, 2=Frozen, 3=DelayedFrozen, 4=Delayed.
        Defaults to 4 (Delayed) for weekend posture.
        """
        try:
            if self._ib:
                self._ib.reqMarketDataType(int(mode))
                self._events.append({"type": "DATA_MODE_SET", "mode": int(mode)})
                self._data_mode = int(mode)
        except Exception as e:
            self._events.append({"type": "DATA_MODE_ERROR", "error": str(e)})

    def is_session_open(self, symbol: str = "MES", exchange: str = "CME", now: Optional[datetime] = None) -> bool:
        """Return True if instrument appears tradable at 'now'.
        Tries contract details liquidHours/tradingHours; falls back to weekend heuristic.
        """
        ts = now or datetime.utcnow()
        # Heuristic fallback: Saturday closed; Sunday opens after 18:00 ET
        try:
            from zoneinfo import ZoneInfo
            ET = ZoneInfo("America/New_York")
            loc = ts.astimezone(ET)
            wd, hr = loc.weekday(), loc.hour
            # Quick guard before detailed check
            if wd == 5:
                return False
            if wd == 6 and hr < 18:
                return False
        except Exception:
            pass

        # Detailed check via contract details
        try:
            import ib_insync as ibis
            if not self._ib:
                return True  # In OBSERVE, allow compute path while skipping execution upstream
            base = ibis.Future(symbol=symbol, exchange=exchange, currency="USD", multiplier='5', tradingClass='MES')
            cds = self._ib.reqContractDetails(base)
            if not cds:
                # No details; rely on heuristic outcome set above
                return False
            # Use first contract liquidHours/tradingHours
            cd = cds[0]
            hours_str = (cd.liquidHours or cd.tradingHours or "").strip()
            if not hours_str:
                # No hours string available; fail-closed
                return False
            # Parse format like "YYYYMMDD:HHMM-HHMM;YYYYMMDD:HHMM-HHMM;..."
            from zoneinfo import ZoneInfo
            ET = ZoneInfo("America/New_York")
            now_et = ts.astimezone(ET)
            now_date = now_et.strftime("%Y%m%d")
            now_time = int(now_et.strftime("%H%M"))
            segments = [seg for seg in hours_str.split(";") if seg]
            for seg in segments:
                try:
                    dpart, tpart = seg.split(":")
                    if dpart != now_date:
                        continue
                    start_str, end_str = tpart.split("-")
                    if start_str == "CLOSED" or end_str == "CLOSED":
                        continue
                    start = int(start_str)
                    end = int(end_str)
                    if start <= now_time <= end:
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            # Fail-closed on parsing or detail errors
            return False

    def req_historical_bars(
        self,
        symbol: str = "MES",
        exchange: str = "CME",
        durationStr: str = "3 D",
        barSizeSetting: str = "5 mins",
        whatToShow: str = "TRADES",
        useRTH: bool = False,
        marketDataType: int = 4,
    ) -> List[Dict[str, Any]]:
        """Request historical bars and return list of dicts {date, open, high, low, close, volume}."""
        out: List[Dict[str, Any]] = []
        try:
            if not self._ib:
                ok = self._ensure_connection()
                if not ok:
                    return out
            import ib_insync as ibis
            self._ib.reqMarketDataType(int(marketDataType))
            base = ibis.Future(symbol=symbol, exchange=exchange, currency="USD", multiplier='5', tradingClass='MES')
            cds = self._ib.reqContractDetails(base)
            if not cds:
                return out
            c = cds[0].contract
            self._ib.qualifyContracts(c)
            bars = self._ib.reqHistoricalData(
                c,
                endDateTime="",
                durationStr=durationStr,
                barSizeSetting=barSizeSetting,
                whatToShow=whatToShow,
                useRTH=useRTH,
                formatDate=1,
            )
            for b in bars:
                out.append({
                    "date": b.date,
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                    "volume": int(b.volume or 0),
                })
            self._events.append({"type": "HISTORICAL_BARS", "count": len(out), "barSize": barSizeSetting, "duration": durationStr})
        except Exception as e:
            self._events.append({"type": "HISTORICAL_BARS_ERROR", "error": str(e)})
        return out

    def get_status(self) -> Dict[str, Any]:
        ts = datetime.utcnow().isoformat()
        connected = bool(self._ib)
        try:
            acct = self.get_account_snapshot()
        except Exception:
            acct = {}
        try:
            open_flag = self.is_session_open()
        except Exception:
            open_flag = False
        # Data quality detection
        dq = "NONE"
        last_tick_ts = None
        last_hist_ts = None
        primary_contract = None
        dte = None
        contract_month = None
        try:
            if self._mes_contract:
                primary_contract = {
                    "conId": getattr(self._mes_contract, "conId", None),
                    "lastTradeDate": getattr(self._mes_contract, "lastTradeDateOrContractMonth", None),
                    "symbol": getattr(self._mes_contract, "symbol", None),
                }
                # Compute DTE
                raw_expiry = getattr(self._mes_contract, "lastTradeDateOrContractMonth", None)
                contract_month = raw_expiry
                if raw_expiry:
                    try:
                        from datetime import date
                        if len(str(raw_expiry)) == 8:
                            expiry_dt = date(int(str(raw_expiry)[0:4]), int(str(raw_expiry)[4:6]), int(str(raw_expiry)[6:8]))
                        else:
                            ym = str(raw_expiry)
                            if len(ym) == 6:
                                expiry_dt = date(int(ym[0:4]), int(ym[4:6]), 20)
                            else:
                                expiry_dt = None
                        if expiry_dt:
                            dte = (expiry_dt - date.today()).days
                    except Exception:
                        dte = None
        except Exception:
            primary_contract = None
        try:
            if self._ib and self._mes_contract:
                t = self._ib.reqMktData(self._mes_contract, "", False, False)
                self._ib.sleep(1.0)
                bid = float(getattr(t, "bid", 0) or 0)
                ask = float(getattr(t, "ask", 0) or 0)
                last = float(getattr(t, "last", 0) or 0)
                last_tick_ts = getattr(t, "time", None)
                if bid or ask or last:
                    if self._data_mode in (1, 2):
                        dq = "LIVE"
                    elif self._data_mode in (3, 4):
                        dq = "DELAYED"
                    else:
                        dq = "UNKNOWN"
                else:
                    # Try a minimal historical check
                    bars = self.req_historical_bars(durationStr="1 D", barSizeSetting="5 mins")
                    if bars:
                        dq = "HISTORICAL_ONLY"
                        last_hist_ts = bars[-1].get("date")
        except Exception:
            pass
        if hasattr(last_tick_ts, "isoformat"):
            last_tick_ts = last_tick_ts.isoformat()
        if hasattr(last_hist_ts, "isoformat"):
            last_hist_ts = last_hist_ts.isoformat()
        return {
            "timestamp": ts,
            "mode": self.mode,
            "connected": connected,
            "execution_enabled": self.execution_enabled,
            "session_open": open_flag,
            "data_mode": self._data_mode,
            "data_quality": dq,
            "last_tick_ts": last_tick_ts,
            "last_hist_bar_ts": last_hist_ts,
            "primary_contract": primary_contract,
            "dte": dte,
            "contract_month": contract_month,
            "account": acct,
        }

    def get_market_context(self, light: bool = True) -> Dict[str, Any]:
        """Return current market context for decision logging and preflight.
        Always returns a fully shaped dict with explicit (non-null) values.
        In light mode, avoid heavy network calls and derive data_quality from data_mode.
        
        Returns:
            Dict with: connected, session_open, execution_enabled, data_mode, data_quality,
                       last_tick_ts, last_hist_bar_ts, primary_contract, dte, contract_month.
        """
        connected = bool(self._ib)
        try:
            session_open = self.is_session_open()
        except Exception:
            session_open = False
        
        data_mode = self._data_mode
        dq = "NONE"  # Default explicit value
        last_tick_ts = None
        last_hist_ts = None
        primary_contract = None
        dte = None
        contract_month = None
        
        # Extract contract info
        try:
            if self._mes_contract:
                primary_contract = {
                    "conId": getattr(self._mes_contract, "conId", None),
                    "lastTradeDate": getattr(self._mes_contract, "lastTradeDateOrContractMonth", None),
                    "symbol": getattr(self._mes_contract, "symbol", None),
                }
                # Compute DTE
                raw_expiry = getattr(self._mes_contract, "lastTradeDateOrContractMonth", None)
                contract_month = raw_expiry
                if raw_expiry:
                    try:
                        from datetime import date
                        if len(str(raw_expiry)) == 8:
                            expiry_dt = date(int(str(raw_expiry)[0:4]), int(str(raw_expiry)[4:6]), int(str(raw_expiry)[6:8]))
                        else:
                            ym = str(raw_expiry)
                            if len(ym) == 6:
                                expiry_dt = date(int(ym[0:4]), int(ym[4:6]), 20)
                            else:
                                expiry_dt = None
                        if expiry_dt:
                            dte = (expiry_dt - date.today()).days
                    except Exception:
                        dte = None
        except Exception:
            primary_contract = None
        
        # Determine data quality
        if light:
            # Light mode: infer from data_mode
            if data_mode in (1, 2):
                dq = "LIVE"
            elif data_mode in (3, 4):
                dq = "DELAYED"
            else:
                dq = "UNKNOWN"
        else:
            # Full mode: probe current market data
            try:
                if self._ib and self._mes_contract:
                    t = self._ib.reqMktData(self._mes_contract, "", False, False)
                    self._ib.sleep(1.0)
                    bid = float(getattr(t, "bid", 0) or 0)
                    ask = float(getattr(t, "ask", 0) or 0)
                    last = float(getattr(t, "last", 0) or 0)
                    last_tick_ts = getattr(t, "time", None)
                    if bid or ask or last:
                        if self._data_mode in (1, 2):
                            dq = "LIVE"
                        elif self._data_mode in (3, 4):
                            dq = "DELAYED"
                        else:
                            dq = "UNKNOWN"
                    else:
                        # Try historical
                        bars = self.req_historical_bars(durationStr="1 D", barSizeSetting="5 mins")
                        if bars:
                            dq = "HISTORICAL_ONLY"
                            last_hist_ts = bars[-1].get("date")
                        else:
                            dq = "NONE"
            except Exception:
                dq = "UNKNOWN"
        
        # Format timestamps
        if hasattr(last_tick_ts, "isoformat"):
            last_tick_ts = last_tick_ts.isoformat()
        if hasattr(last_hist_ts, "isoformat"):
            last_hist_ts = last_hist_ts.isoformat()
        
        return {
            "connected": connected,
            "session_open": session_open,
            "execution_enabled": self.execution_enabled,
            "data_mode": data_mode,
            "data_quality": dq,
            "last_tick_ts": last_tick_ts,
            "last_hist_bar_ts": last_hist_ts,
            "primary_contract": primary_contract,
            "dte": dte,
            "contract_month": contract_month,
        }

    def _resolve_primary_contract(self, symbol: str = "MES", exchange: str = "CME", min_days_to_expiry: int = 5) -> Any:
        """Select nearest non-expired contract deterministically.
        
        Args:
            symbol: Futures symbol (default "MES").
            exchange: Exchange code (default "CME").
            min_days_to_expiry: Minimum days until expiry to consider contract (default 5).
                                Prevents trading contracts about to roll. Falls back to nearest
                                non-expired if nothing matches.
        
        Returns:
            Contract object or base contract spec.
        """
        try:
            import ib_insync as ibis
            base = ibis.Future(symbol=symbol, exchange=exchange, currency="USD", multiplier='5', tradingClass='MES')
            cds = self._ib.reqContractDetails(base)
            if not cds:
                return base
            # Choose the nearest with a valid lastTradeDateOrContractMonth
            from datetime import date
            today = date.today()
            def _parse(dstr: str):
                try:
                    if len(dstr) == 8:
                        return date(int(dstr[0:4]), int(dstr[4:6]), int(dstr[6:8]))
                    # YYYYMM format fallback: assume 20th
                    if len(dstr) == 6:
                        return date(int(dstr[0:4]), int(dstr[4:6]), 20)
                except Exception:
                    return None
                return None
            
            eligible = []
            all_valid = []
            for cd in cds:
                d = _parse(getattr(cd.contract, "lastTradeDateOrContractMonth", ""))
                if d and d >= today:
                    dte = (d - today).days
                    all_valid.append((d, dte, cd.contract))
                    # Filter by min_days_to_expiry
                    if dte >= min_days_to_expiry:
                        eligible.append((d, cd.contract))
            
            # Prefer contract with sufficient DTE
            if eligible:
                eligible.sort(key=lambda x: x[0])
                return eligible[0][1]
            
            # Fallback: use nearest non-expired
            if all_valid:
                all_valid.sort(key=lambda x: x[0])
                return all_valid[0][2]
            
            return cds[0].contract
        except Exception:
            return self._mes_contract or symbol

    def flatten_positions(self) -> None:
        if self.mode == "LIVE" and self._ib:
            try:
                # Enforce execution gate before sending flatten orders
                self.assert_execution_allowed(reason_context={"action": "FLATTEN"})
                positions = self._ib.positions()
                for pos in positions:
                    if pos.contract.symbol == "MES" and pos.position != 0:
                        import ib_insync as ibis
                        action = "SELL" if pos.position > 0 else "BUY"
                        order = ibis.MarketOrder(action=action, totalQuantity=abs(pos.position))
                        self._ib.placeOrder(pos.contract, order)
                        self._events.append({"type": "FLATTEN_SUBMITTED", "position": pos.position})
            except Exception as e:
                self._events.append({"type": "FLATTEN_ERROR", "error": str(e)})

    def get_position_snapshot(self) -> Dict[str, Any]:
        if self.mode == "LIVE" and self._ib:
            try:
                snap = self.account.get_position_snapshot()
                if snap["position"] != 0:
                    return snap
            except Exception:
                pass
        return self.account.get_position_snapshot()

    def get_account_snapshot(self) -> Dict[str, Any]:
        """Return account summary: equity, buying power, margin."""
        if self.mode == "LIVE" and self._ib:
            try:
                # Prefer direct ib_insync account summary for reliability
                vals = list(self._ib.accountSummary())
                if not vals:
                    try:
                        self._ib.sleep(0.5)
                        vals = list(self._ib.accountSummary())
                    except Exception:
                        pass
                tags = {getattr(v, 'tag', ''): getattr(v, 'value', '') for v in vals if getattr(v, 'tag', None)}
                def _f(name: str) -> float:
                    try:
                        return float(tags.get(name, 0) or 0)
                    except Exception:
                        return 0.0
                return {
                    "equity": _f("NetLiquidation"),
                    "buying_power": _f("BuyingPower") or _f("AvailableFunds"),
                    "maintenance_margin": _f("MaintMarginReq"),
                    "initial_margin": _f("InitMarginReq"),
                    "realized_pnl": _f("RealizedPnL"),
                    "unrealized_pnl": _f("UnrealizedPnL"),
                    "raw": tags,
                }
            except Exception:
                pass
        # OBSERVE or fallback
        return {
            "equity": 0.0,
            "buying_power": 0.0,
            "maintenance_margin": 0.0,
            "initial_margin": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
        }

    def place_order(self, intent_obj: Any, last_price: Any) -> Dict[str, Any]:
        """Place order via IBKR; idempotent on intent_id."""
        now = datetime.utcnow()
        intent_id = getattr(intent_obj, "intent_id", None) or f"intent-{int(now.timestamp()*1000)}"
        
        # Idempotency check
        if intent_id in self._idempotent_orders:
            oid = self._idempotent_orders[intent_id]
            return {
                "order_id": oid,
                "status": "IDEMPOTENT_REPEAT",
                "filled_delta": 0
            }
        
        # Constitutional pre-filter
        pos = self.get_position_snapshot().get("position", 0)
        state = ConstitutionalState(
            daily_loss=0.0,
            consecutive_losses=0,
            trades_today=len(self._open_orders),
            current_position=int(pos or 0),
            current_time_et=now.strftime("%H:%M"),
            current_dvs=float(getattr(intent_obj, "dvs", 1.0)),
            current_eqs=float(getattr(intent_obj, "eqs", 1.0)),
        )
        allow, reason = filter_order_intent(vars(intent_obj), state, Constitution())
        if allow != "ALLOW":
            return {"type": "ORDER_REJECTED", "reason": reason}

        # Generate client order ID (IBKR idempotency key)
        client_oid = f"{intent_id}-{int(now.timestamp())}"
        oid = client_oid
        self._open_orders[oid] = {
            "status": "NEW",
            "created_at": now.isoformat(),
            "intent_id": intent_id,
            "direction": getattr(intent_obj, "direction", "LONG"),
            "contracts": int(getattr(intent_obj, "contracts", 1)),
        }
        self._idempotent_orders[intent_id] = oid
        
        self._events.append({"type": "ORDER", "order_id": oid, "status": "NEW", "created_at": now.isoformat()})
        
        if self.mode == "OBSERVE":
            # OBSERVE mode: simulate order ack without fill
            self._open_orders[oid]["status"] = "ACCEPTED"
            self._events.append({"type": "ORDER_ACK", "order_id": oid, "status": "ACCEPTED", "timestamp": now.isoformat()})
        else:
            # LIVE mode: submit bracket via ib_insync
            try:
                if not self._ensure_connection():
                    self._open_orders[oid]["status"] = "REJECTED"
                    self._events.append({"type": "ORDER_REJECTED", "order_id": oid, "reason": "connection_failed"})
                    return {"type": "ORDER_REJECTED", "reason": "connection_failed"}
                
                import ib_insync as ibis
                direction = getattr(intent_obj, "direction", "LONG")
                action = "BUY" if direction == "LONG" else "SELL"
                qty = int(getattr(intent_obj, "contracts", 1))
                limit_price = float(getattr(intent_obj, "limit_price", last_price))
                bracket = getattr(intent_obj, "metadata", {}).get("bracket", {})
                stop_price = float(bracket.get("stop_price", 0.0))
                target_price = float(bracket.get("target_price", 0.0))
                # Hard invariant: enforce execution allowed before any placeOrder()
                try:
                    self.assert_execution_allowed(reason_context={
                        "order_id": oid,
                        "action": action,
                        "qty": qty,
                        "limit_price": limit_price,
                    })
                except IBKRAdapter.ExecutionNotAllowedError as gate_err:
                    self._open_orders[oid]["status"] = "REJECTED"
                    self._events.append({"type": "ORDER_REJECTED", "order_id": oid, "reason": str(gate_err)})
                    return {"type": "ORDER_REJECTED", "reason": str(gate_err)}
                
                # Create bracket with clientId for idempotency
                bracket_orders = ibis.order.bracketOrder(action, qty, limit_price, target_price, stop_price)
                for o in bracket_orders:
                    o.clientId = int(client_oid.split("-")[1])  # Idempotent key
                    self._ib.placeOrder(self._mes_contract, o)
                
                self._open_orders[oid]["status"] = "SUBMITTED"
                self._events.append({"type": "ORDER_SUBMITTED", "order_id": oid, "status": "SUBMITTED", "timestamp": now.isoformat()})
            except Exception as e:
                self._open_orders[oid]["status"] = "REJECTED"
                self._events.append({"type": "ORDER_REJECTED", "order_id": oid, "reason": str(e)})
                return {"type": "ORDER_REJECTED", "reason": str(e)}
        
        return {"order_id": oid, "status": self._open_orders[oid]["status"], "filled_delta": 0}

    def on_cycle(self, ts: datetime) -> None:
        """Periodic housekeeping: heartbeat, reconcile, process fill events, market data quality."""
        if self.mode == "LIVE" and self._ib:
            self.conn.heartbeat()
            self.market_data.heartbeat()
            
            # Process any pending fill events
            fills = self.orders_monitor.pop_fills()
            for fill in fills:
                self._events.append(fill)
            
            # Emit market data quality check
            data_quality = self.market_data.get_quality_score()
            self._events.append({"type": "DATA_QUALITY_CHECK", "quality_score": data_quality})

    def get_market_data_quality(self) -> float:
        """Return current market data quality score (0.0 - 1.0)."""
        return self.market_data.get_quality_score()

    def get_last_bar(self) -> Optional[Dict[str, Any]]:
        """Return the last received 1-minute bar."""
        return self.market_data.get_last_bar()

    def pop_events(self) -> List[Dict[str, Any]]:
        ev, self._events = self._events, []
        return ev

    def get_open_orders(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._open_orders)

    def cancel_order(self, order_id: str) -> bool:
        od = self._open_orders.get(order_id)
        if not od:
            return False
        od["status"] = "CANCELED"
        if self.mode == "LIVE" and self._ib:
            try:
                # Cancel via broker
                import ib_insync as ibis
                self._ib.cancelOrder(od.get("broker_id", order_id))
            except Exception:
                pass
        self._events.append({"type": "ORDER_CANCELED", "order_id": order_id})
        return True
