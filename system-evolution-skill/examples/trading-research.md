# Example: Trading Research

## User Problem

My 5-minute market strategy keeps losing during reversals.

## Problem Type

Trading / Strategy Research.

This example is for research, simulation, and risk diagnosis only. It is not an instruction to deploy real funds.

## System Boundary

Inside:
- market price
- order book
- signal generator
- execution logic
- risk budget
- logs
- replay engine

Outside:
- uncontrollable market shocks
- platform outages
- other participants' private strategies

## Information Layer

Inputs:
- price movement
- volatility
- time remaining
- liquidity
- bid/ask spread
- fill quality
- previous decision trace

Noise:
- short-term false breakouts
- delayed price feeds
- thin order book effects

## Energy / Resource Layer

Resources:
- risk budget
- capital exposure
- API reliability
- execution speed
- data quality
- emotional tolerance for drawdown

## Feedback Layer

Metrics:
- reversal rate
- bad fill rate
- maximum adverse movement
- fill-to-result delay
- realized PnL in simulation
- loss cause tags

## Failure Diagnosis

Likely failures:
- signal too short-term and noisy
- execution friction eats edge
- entries occur before signal confirmation
- feedback logs do not distinguish loss causes

## Smallest Useful Experiment

Hypothesis:
Most losses are caused by immediate reversal after entry, not by final direction error.

Action:
Replay historical windows and tag every simulated loss as wrong direction, immediate reversal, late reversal, bad fill, spread loss, or no exit.

Success metric:
A dominant loss category explains more than 40% of losses.

Failure metric:
Losses are evenly distributed and no clear bottleneck appears.

## Evolution Roadmap

Keep:
- signal rules that survive replay after execution friction

Remove:
- rules that only work before spread/latency assumptions

Amplify:
- logging and cause tagging

Test next:
- entry timing filters in simulation only
