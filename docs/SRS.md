# Software Requirement Specification (SRS) – AI Travel Planner

## 1. Introduction
- **Purpose:** Build a web app that auto-generates travel itineraries using AI and real-world data (Google Places, TripAdvisor).
- **Scope:** Support user input, AI planning, visualization, export.

## 2. Actors & Use Cases
Guest, User, Admin.

## 3. Functional Requirements
FR1: Input data. FR2: AI generation. FR3: Fetch real places. FR4: Optimize route. FR5: Export plan. FR6: Auth.

## 4. Non-Functional
JWT, caching, uptime ≥99%, scalability, multilingual.

## 5. Constraints
Limited API quota. No real booking.

## 6. Acceptance Criteria
Generate real-data itinerary with map and export.