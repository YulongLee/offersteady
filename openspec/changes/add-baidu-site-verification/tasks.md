## 1. Verification marker

- [x] 1.1 Add the approved Baidu site verification meta tag to the public homepage head
- [x] 1.2 Add a regression test that checks the marker name, value, placement, and uniqueness

## 2. Validation and delivery

- [x] 2.1 Run the focused test, Web production build, and strict OpenSpec validation
- [x] 2.2 Deploy only the Web static service and verify the marker from the public homepage source

## 3. www verification reachability repair

- [x] 3.1 Remove the Web-layer cross-domain redirect for the registered `www` site property and add a regression test
- [ ] 3.2 Run focused tests, production build, strict OpenSpec validation, then deploy only Web and verify both hostnames
