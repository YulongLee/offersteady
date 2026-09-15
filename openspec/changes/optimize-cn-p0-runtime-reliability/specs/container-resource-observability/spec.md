## ADDED Requirements

### Requirement: Separate container and host memory measurements
The capacity API SHALL report backend container memory usage from the container's current RSS/cgroup usage and SHALL report host memory as a separate field; a host fallback MUST NOT be labeled as container memory.

#### Scenario: Container has no memory limit
- **WHEN** the backend runs without a cgroup memory limit
- **THEN** the API reports container RSS usage and a distinct host memory percentage

#### Scenario: Capacity dashboard renders memory
- **WHEN** an administrator views capacity metrics
- **THEN** the labels and descriptions identify container memory and host memory separately
