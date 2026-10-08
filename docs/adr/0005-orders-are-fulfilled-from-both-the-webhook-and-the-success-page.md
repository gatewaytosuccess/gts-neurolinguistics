# Orders are fulfilled from both the Stripe webhook and the success page

Payment happens on Stripe's hosted Checkout, so we learn of it two ways: the `checkout.session.completed` webhook, and the learner landing on `/checkout/success`. Either can arrive first and either can fail to arrive, so both call the same fulfil function, which locks the order and turns a paid order into enrollments exactly once. The success page is a `GET` that writes; that is deliberate, so a learner has access the moment they return even if the webhook is late.

## Consequences

- **The order exists before payment.** Starting a checkout creates a `pending` order with its price snapshot and puts its id in the session's metadata; fulfilment never builds an order from a session. An unpaid session expires the order.
- **Fulfil must stay idempotent.** Anything added to it — an email, a coupon redemption — has to happen once per order no matter how many times it runs.
- **Neither path trusts the other's input.** The success page re-fetches the session from Stripe rather than trusting the query string, and both check the amount and currency against the order before enrolling anyone.

## Considered options

- **Webhook only**: the success page polls until the order is paid. Rejected: a slow or failing webhook leaves a learner who has paid staring at a spinner.
- **Success page only**: rejected, because a closed tab would leave a paid order with no enrollment.
