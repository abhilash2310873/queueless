# HTTP API

Pages and JSON used by the app:

- `GET /browse` search and filters
- `POST /api/cart/add` form fields `food_id`, `quantity`
- `POST /api/cart/update` form fields `food_id`, `quantity`
- `POST /checkout` form fields `slot_id`, `method` (`CASH` or `ONLINE`)
- `GET /orders/<id>`
- `GET /orders/<id>/status` JSON status, queue, payment, wait
- `GET /orders/<id>/qr` PNG of the signed token
- `POST /payment/<id>/success` and `/failure` mock gateway
- `POST /owner/orders/<id>/accept|preparing|ready|reject|cash`
- `POST /owner/orders/<id>/collect` form field `token`

Students receive 403 on `/admin/users`. Owners receive 403 for another stall's orders.
