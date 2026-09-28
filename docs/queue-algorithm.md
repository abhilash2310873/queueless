# Queue waiting time

Estimated wait = workload ahead ÷ active counters.

Workload ahead is the sum of `preparation minutes × quantity` for every order at the same stall that was created earlier and is still PENDING, ACCEPTED, PREPARING, or READY.

Active counters is `stalls.active_counters` (at least 1). The result is rounded up to whole minutes. A stall with no orders ahead shows 0 minutes. The number is not random.

Queue position is the count of those earlier orders plus one. Each stall has its own queue.
