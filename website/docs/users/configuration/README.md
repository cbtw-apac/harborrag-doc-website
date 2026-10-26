---
title: Configuration
description: 'HarborRAG currently has four independent configuration paths:'
sidebar_position: 10
custom_edit_url: https://github.com/cbtw-apac/HarborRAG/edit/main/docs/users/configuration/README.md
source_path: docs/users/configuration/README.md
source_sha: 217521ac92f0d1f570da22f96551954502e74c1c
---

HarborRAG currently has four independent configuration paths:

1. [Connector Configuration](connector-config.md) - versioned YAML loaded by `harborrag-runtime`.
2. [Parser Configuration](parser-config.md) - versioned YAML loaded by `harborrag-runtime`.
3. [Model Configuration](model-config.md) - YAML or JSON loaded by the chat, embedding, and reranking clients in `harborrag-adapters`.
4. [Temporal Configuration](https://github.com/cbtw-apac/HarborRAG/blob/main/deploy/temporal/README.md) - versioned YAML for connection policy, workers, queues, retries, and workflow timeouts.

[Engine Configuration](config-file-reference.md) documents the small code-constructed engine dataclasses. [Tenant and Workspace Status](workspace-mode.md) explains tenant-aware repository context and what is not yet available as a workspace feature.

For the composed chat surfaces and stored prompt catalog, see
[Chat](../chat/README.md). For MCP tool defaults, limits, tenant overrides, and
the authenticated configuration UI, see
[MCP Setup and Integration](../detailed-guides/mcp-server/setup-and-integration.md).

The checked-in `*.example.yaml` and `.env.*.example` files are references, not automatically loaded runtime files. Copy them for an environment or pass their paths explicitly. HarborRAG does not automatically load dotenv files.
