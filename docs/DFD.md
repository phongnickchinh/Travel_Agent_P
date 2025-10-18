```mermaid
flowchart LR
User([User]) --> Planner[(AI Planner)]
Planner -->|Places API| G[Google]
Planner -->|TripAdvisor API| T[TripAdvisor]
Planner --> DB[(MongoDB)]
```