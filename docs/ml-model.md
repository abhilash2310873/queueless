# Demand levels

`app/queue/predictor.py` counts past orders for a stall by hour. It labels the current hour LOW, MEDIUM, or HIGH by comparing that hour with the average hour that has any orders. Hours 12 and 13 are treated as the lunch peak.

The seed script builds several weeks of synthetic orders. Those rows are not real campus sales. Predictions will change once real orders replace them. The screen shows a level, not a precise count, so it does not pretend to be a high-accuracy model.
