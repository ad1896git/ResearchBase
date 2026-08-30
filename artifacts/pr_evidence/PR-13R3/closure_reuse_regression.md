# Closure reuse regression

Previously accepted request-local reuse remains intact: Claim closure is evaluated once per trace;
Run closure is evaluated at most once per unique Run. The 3-path/1-Run fixture remains 1/1 and the
12-path/9-Run fixture remains 1/9. Increasing paths without increasing unique Runs does not increase
Run closure calls. No global or persistent cache exists.

