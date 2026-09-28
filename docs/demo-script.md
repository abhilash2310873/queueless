# Demo script

Accounts after `flask --app run.py create-admin` and a stall owner you create in the admin screens, or the ones you register during the demo.

1. Open `/auth/register` and try `student@gmail.com`. Say: the college domain is an environment setting, not a hard-coded address.
2. Register `student@college.edu`, read the code in the Flask terminal, verify, and log in.
3. Open Browse. Show an item the owner marked unavailable or with stock 0. The button is sold out.
4. Add a food, then try a second stall. The cart says to clear it or check out separately, because one order is one kitchen queue.
5. Add a pickup slot as the owner, then check out with cash. Show the queue number and the wait, which comes from prep time divided by counters.
6. As the owner, mark cash paid, accept, preparing, ready. The student page polls and shows the new step.
7. Paste the pickup token. A second paste says the order was already collected. Change one character and it is rejected.
8. Log in as a second owner or the student and open `/admin/users`. That is 403 even if the link is typed by hand.
9. Open the admin dashboard. The charts are counts, not a ranking of a best stall.
