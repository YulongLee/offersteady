## 1. Backend connection ownership

- [x] 1.1 Add recent-device lookup for the authenticated user without exposing the full machine code.
- [x] 1.2 Support binding by explicit machine code or the user's last device through one API operation.
- [x] 1.3 Supersede other user and device bindings, close old publishers, and end another live interview.

## 2. Web preparation experience

- [x] 2.1 Add “connect last device” and “enter machine code” choices to the preparation page.
- [x] 2.2 Require a binding created for the current interview before enabling start.
- [x] 2.3 Add responsive styling and clear switching copy without changing the prototype layout.

## 3. Desktop lifecycle recovery

- [x] 3.1 Recreate the publisher when binding identity changes and classify permanent publisher creation failures.
- [x] 3.2 Prevent permanent authorization and replacement errors from entering an infinite retry loop.

## 4. Verification

- [x] 4.1 Add backend regression coverage for one active realtime interview per user.
- [x] 4.2 Add web coverage for both device selection paths and current-session readiness.
- [x] 4.3 Add desktop coverage for terminal publisher errors and validate the OpenSpec change.
