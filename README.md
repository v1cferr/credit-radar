# CreditRadar

Personal credit intelligence and readiness system for the Brazilian credit market.

CreditRadar consolidates credit information that is fragmented across bureaus
(Serasa, Quod, SPC, Equifax/BoaVista), Banco Central do Brasil (SCR/Registrato and
public market datasets), financial institutions and creditors, in order to build a
**historical and explainable** view of a single person's credit position.

It is not a debt tracker. It is built to answer decision questions:

- What debts exist under the CPF, and where can each be settled for the lowest total cost?
- Are there active negative records?
- How are the different bureau scores evolving, and what correlates with the changes?
- What credit exposure currently exists?
- Am I ready to finance a vehicle or a property?
- Is a given financing offer competitive against current market conditions?
- Should I take credit now, or wait for better personal or macroeconomic conditions?

Tracked in Jira as [V1C-76](https://v1cferr.atlassian.net/browse/V1C-76), which is the
primary product specification for this repository.

## Status

Early bootstrap. See the roadmap below for what exists and what does not.

## Safety invariant

CreditRadar **never** performs a financial action on its own. It does not accept
settlement agreements, generate payments, authorize transactions, request loans, apply
for financing or open financial products. It observes, normalizes and explains;
every operation that creates a financial obligation requires explicit human action
outside this system.

Its internal readiness indicators are **heuristics owned by this project**. They are
not predictions of any bank's or bureau's proprietary approval model.
