# AML Suspicious Activity Indicators (Demo Template)

> Status: DEMO TEMPLATE (non-authoritative)
> Purpose: Provide explainable, citable text snippets for the Risk Platform demo.
> Replace with your organization's official AML policy before production use.

## 1. Scope
This document lists common suspicious activity indicators used for AML monitoring and investigations. Indicators are meant to guide review and do not constitute automated enforcement decisions.

## 2. Transaction Velocity & Burst Patterns

### 2.1 High-Velocity Transfers
A sudden spike in the number of outgoing or incoming transfers within a short time window may indicate:
- Account takeover attempts
- Mule activity
- Fraud automation / scripted behavior

Typical evidence includes counts (e.g., transfers per hour), short inter-transaction intervals, and deviation from historical baselines.

### 2.2 Structured or Repetitive Transfers
Repeated transfers with similar amounts, recipients, or timing patterns may indicate structuring or attempts to avoid controls.

### 2.3 Rapid Fund Movement
Funds moving quickly through the account (incoming followed by immediate outgoing) can indicate layering behavior.

## 3. Amount & Behavioral Anomalies

### 3.1 Amount Anomaly vs Historical Pattern
Transfers that significantly deviate from the customer’s historical norms (e.g., 24h/7d average) may indicate abnormal behavior requiring review.

### 3.2 Large Transfers Shortly After Account Creation
Large outbound activity soon after onboarding or shortly after a dormant period can indicate elevated risk.

## 4. Geolocation & Access Inconsistencies

### 4.1 Location Mismatch
A mismatch between:
- profile country / typical country, and
- transaction origination signals (IP, device region, merchant location),
may indicate compromised credentials or account misuse.

### 4.2 Unusual Device / Network Changes
Sudden changes in device identifiers, IP ranges, or network patterns can indicate takeover or shared access.

## 5. Network / Relationship Signals

### 5.1 Links to Known Risky Clusters
Accounts linked to known risky clusters (shared devices, shared withdrawal destinations, repeated counterparties) should be prioritized for review.

## 6. Investigation Notes
Indicators should be evaluated with supporting evidence and context. When evidence is incomplete, investigators should request missing information or cross-check additional sources.