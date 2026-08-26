# Village Market v79 – MSG91 60-second resend

- OTP resend button is disabled for 60 seconds after the first OTP request.
- OTP resend button is disabled for 60 seconds after every resend.
- Keep MSG91 Widget Settings > Resend After set to 60 seconds so server and UI match.
- If OTP is accepted by the widget but SMS is not delivered, check MSG91 OTP/SendOTP logs for Delivered/Pending/Failed status and failure reason.
