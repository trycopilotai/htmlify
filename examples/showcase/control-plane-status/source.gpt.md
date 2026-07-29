---
title: Cross-machine Release Control Path
---

# Cross-machine Release Control Path

**Status:** Operational through request and status
reporting. Release remains on hold until digest verification
and restart evidence are complete.

## Control path

1. The workstation writes a durable release request.
2. The authenticated relay forwards the request identifier.
3. The build worker reads the request and records progress.
4. The worker publishes a digest-pinned candidate.
5. The workstation reads the durable status record.

## Boundaries

| Boundary          | Responsibility                    | Durable evidence    |
| ----------------- | --------------------------------- | ------------------- |
| Workstation       | Create request and inspect status | Request identifier  |
| Relay             | Authenticate and forward          | Reachability result |
| Build worker      | Build, test, and publish          | Job and test record |
| Artifact registry | Store the candidate               | Candidate digest    |
| Service host      | Restart the pinned candidate      | Restart result      |

## Current evidence

| Check              | State   | Evidence                               |
| ------------------ | ------- | -------------------------------------- |
| Request record     | Pass    | Identifier and creation time recorded  |
| Relay reachability | Pass    | Authenticated probe completed          |
| Worker job         | Pass    | Build and test result recorded         |
| Candidate digest   | Pending | Registry and status digests must match |
| Service restart    | Pending | Restart result has not been recorded   |

## Release sequence

1. Compare the candidate digest with the durable status.
2. Restart the service with the matching digest.
3. Record the restart result and final probe.

## Reading rule

Treat live process output as supporting evidence. Treat the
durable request, status, digest, and restart records as the
release record.

## Source note

This is synthetic example material created to demonstrate
HTMLify. It does not describe a real control plane.
