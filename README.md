# solar-bess-grid-connection-study
This project assesses whether a 20 MW solar farm and 10 MW battery plant can connect to a 132 kV network without breaching voltage, thermal or fault-level limits. It uses Python and pandapower to run load flow and fault level studies across several operating cases, check grid strength, and test fixes for any problems found. It is a self-directed learning project using a simplified network with assumed data, not real utility data.

## Assessment criteria

Limits marked "assumed" are my own choices and have no official source.

| # | Check | Limit | Source type | Ref |
|---|---|---|---|---|
| 1 | Continuous operation voltage | 90% to 110% of normal voltage | NER / AEMO | [1] S5.2.5.4 |
| 2 | Reactive power capability | At least 0.395 x rated MW, both directions (about 11.9 MVAr at 30 MW) | NER / AEMO | [1] S5.2.5.1 |
| 3 | Voltage control | Setpoint adjustable over 95% to 105%, held within 0.5% | NER / AEMO | [1] S5.2.5.13(4) |
| 4 | Normal voltage | 0.95 to 1.05 pu | Network operator (assumed) | [3] gives no numbers |
| 5 | Post-contingency voltage | 0.90 to 1.10 pu | Network operator (assumed) | Consistent with [1] |
| 6 | Line and transformer loading | 100% of continuous rating | Network operator (assumed) | Standard practice |
| 7 | Switchgear breaking current | 25 kA | Datasheet | [4] |
| 8 | Switchgear peak withstand | 63 kA | Datasheet | [4] |
| 9 | Switchgear feeder current | 1250 A | Datasheet | [4] |
| 10 | Short circuit ratio (screening) | Above about 3 | Rule of thumb | [5] gives no threshold |

## References

1. [AEMO, Generator Performance Standards template](https://www.aemo.com.au/-/media/files/electricity/nem/network_connections/generator-performance-standards-template.docx?la=en)
2. [AEMC, National Electricity Rules, Chapter 5](https://www.aemc.gov.au/sites/default/files/2018-07/NER%20-%20v111%20-%20Chapter%205.docx)
3. [Transgrid, 2021 Transmission Annual Planning Report](https://aer.gov.au/system/files/Transgrid%20-%202021%20Transmission%20Annual%20Planning%20Report%20-%2030%20Jul%202021%20-%20PUBLIC.pdf)
4. [Siemens, NXPLUS C switchgear catalogue](https://assets.new.siemens.com/siemens/assets/api/uuid:97558e98-d760-4d9b-8149-17d982f3af56/NXPLUS-C-HA35-41-en_original.pdf)
5. [AEMO, System Strength Explained](https://www.aemo.com.au/-/media/files/electricity/nem/system-strength-explained.pdf?la=en)
