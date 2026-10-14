# Demand model

`app/queue/predictor.py` trains `sklearn.linear_model.LinearRegression` when a stall has at least eight past orders. The features are the day of the week and the hour. The target is how many orders fell in that pair. The screen shows LOW, MEDIUM, or HIGH by comparing the prediction with the average hour, not a fake precise count.

The training rows come from `scripts/seed_data.py` until students place real orders. That script builds about five weeks of synthetic history with a lunch peak between 12:45 and 13:30, lighter evenings, and fewer weekend orders. Those rows are not real campus sales. Predictions change when real orders replace them.

Sell-out lines on the kitchen page use the same history. If at least half of an item's orders fall between 12:45 and 13:30, the page says that item frequently sells out in that window.
