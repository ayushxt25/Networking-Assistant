from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from typing import Optional

from sqlalchemy.orm import Session

from app.db_models import Contact, Event, FollowUp, Interaction


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


@dataclass
class GraphContactScore:
    contact_id: int
    name: str
    centrality_score: float
    interaction_count: int
    shared_signal_count: int


@dataclass
class GraphContactInsight:
    contact_id: int
    name: str
    reason: str


@dataclass
class GraphCluster:
    cluster_id: str
    contact_ids: list[int]
    contact_names: list[str]
    shared_signals: list[str]


@dataclass
class NetworkGraphInsights:
    total_contacts: int
    network_density_estimate: float
    centrality_scores: list[GraphContactScore]
    weak_tie_candidates: list[GraphContactInsight]
    strong_tie_contacts: list[GraphContactInsight]
    bridge_contacts: list[GraphContactInsight]
    isolated_contacts: list[GraphContactInsight]
    clusters: list[GraphCluster]
    created_at: datetime


def get_network_graph_insights(db: Session, user_id: int) -> NetworkGraphInsights:
    contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()
    follow_ups = db.query(FollowUp).filter(FollowUp.user_id == user_id).all()
    events = db.query(Event).filter(Event.user_id == user_id).all()

    if not contacts:
        return NetworkGraphInsights(
            total_contacts=0,
            network_density_estimate=0.0,
            centrality_scores=[],
            weak_tie_candidates=[],
            strong_tie_contacts=[],
            bridge_contacts=[],
            isolated_contacts=[],
            clusters=[],
            created_at=_utcnow(),
        )

    contact_by_id = {contact.id: contact for contact in contacts}
    event_titles = {event.id: event.title for event in events}
    interaction_counts: dict[int, int] = defaultdict(int)
    event_ids_by_contact: dict[int, set[int]] = defaultdict(set)
    follow_up_counts: dict[int, int] = defaultdict(int)

    for interaction in interactions:
        if interaction.contact_id is not None and interaction.contact_id in contact_by_id:
            interaction_counts[interaction.contact_id] += 1
            if interaction.event_id is not None:
                event_ids_by_contact[interaction.contact_id].add(interaction.event_id)

    for follow_up in follow_ups:
        if follow_up.contact_id is not None and follow_up.contact_id in contact_by_id:
            follow_up_counts[follow_up.contact_id] += 1
            if follow_up.event_id is not None:
                event_ids_by_contact[follow_up.contact_id].add(follow_up.event_id)

    adjacency: dict[int, set[int]] = {contact.id: set() for contact in contacts}
    edge_signals: dict[frozenset[int], set[str]] = defaultdict(set)

    for left, right in combinations(contacts, 2):
        signals: set[str] = set()
        left_tags = set(_split_csv(left.tags))
        right_tags = set(_split_csv(right.tags))
        shared_tags = sorted(left_tags & right_tags)
        if shared_tags:
            signals.update(f"tag:{tag}" for tag in shared_tags)
        if left.company.strip().lower() == right.company.strip().lower():
            signals.add(f"company:{left.company.strip().lower()}")
        if left.role.strip().lower() == right.role.strip().lower():
            signals.add(f"role:{left.role.strip().lower()}")

        shared_event_ids = sorted(event_ids_by_contact[left.id] & event_ids_by_contact[right.id])
        for event_id in shared_event_ids:
            signals.add(f"event:{event_titles.get(event_id, str(event_id)).lower()}")

        if signals:
            adjacency[left.id].add(right.id)
            adjacency[right.id].add(left.id)
            edge_signals[frozenset({left.id, right.id})].update(signals)

    centrality_scores: list[GraphContactScore] = []
    strong_tie_contacts: list[GraphContactInsight] = []
    weak_tie_candidates: list[GraphContactInsight] = []
    bridge_contacts: list[GraphContactInsight] = []
    isolated_contacts: list[GraphContactInsight] = []

    for contact in contacts:
        degree = len(adjacency[contact.id])
        interaction_count = interaction_counts[contact.id]
        strength = contact.relationship_strength or 0
        event_count = len(event_ids_by_contact[contact.id])
        signal_count = len(
            {
                signal
                for neighbor in adjacency[contact.id]
                for signal in edge_signals[frozenset({contact.id, neighbor})]
            }
        )
        centrality_score = round(strength * 2.0 + interaction_count * 3.0 + degree * 2.0 + event_count, 2)
        centrality_scores.append(
            GraphContactScore(
                contact_id=contact.id,
                name=contact.name,
                centrality_score=centrality_score,
                interaction_count=interaction_count,
                shared_signal_count=signal_count,
            )
        )

        if degree == 0 and interaction_count == 0:
            isolated_contacts.append(
                GraphContactInsight(
                    contact_id=contact.id,
                    name=contact.name,
                    reason="No shared tags, company, role, or event links with other contacts.",
                )
            )

        if strength >= 4 or interaction_count >= 2:
            strong_tie_contacts.append(
                GraphContactInsight(
                    contact_id=contact.id,
                    name=contact.name,
                    reason=f"Relationship strength {strength} with {interaction_count} interaction(s).",
                )
            )
        elif degree > 0 and strength <= 3 and interaction_count <= 1:
            weak_tie_candidates.append(
                GraphContactInsight(
                    contact_id=contact.id,
                    name=contact.name,
                    reason=f"Light relationship signal: strength {strength} with {interaction_count} interaction(s).",
                )
            )

        neighbor_companies = {contact_by_id[neighbor].company.strip().lower() for neighbor in adjacency[contact.id]}
        neighbor_signal_types = {
            signal.split(":", 1)[0]
            for neighbor in adjacency[contact.id]
            for signal in edge_signals[frozenset({contact.id, neighbor})]
        }
        if degree >= 2 and (len(neighbor_companies) >= 2 or len(neighbor_signal_types) >= 2):
            bridge_contacts.append(
                GraphContactInsight(
                    contact_id=contact.id,
                    name=contact.name,
                    reason="Connects across multiple companies, tags, roles, or shared events.",
                )
            )

    visited: set[int] = set()
    clusters: list[GraphCluster] = []
    cluster_index = 1
    for contact in contacts:
        if contact.id in visited or not adjacency[contact.id]:
            continue
        stack = [contact.id]
        component: list[int] = []
        component_signals: set[str] = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            for neighbor in adjacency[current]:
                component_signals.update(edge_signals[frozenset({current, neighbor})])
                if neighbor not in visited:
                    stack.append(neighbor)
        component.sort()
        if len(component) >= 2:
            clusters.append(
                GraphCluster(
                    cluster_id=f"cluster-{cluster_index}",
                    contact_ids=component,
                    contact_names=[contact_by_id[contact_id].name for contact_id in component],
                    shared_signals=sorted(component_signals),
                )
            )
            cluster_index += 1

    possible_edges = len(contacts) * (len(contacts) - 1) / 2
    actual_edges = sum(len(neighbors) for neighbors in adjacency.values()) / 2
    density = round(actual_edges / possible_edges, 2) if possible_edges else 0.0

    centrality_scores.sort(key=lambda item: (-item.centrality_score, item.name.lower(), item.contact_id))
    strong_tie_contacts.sort(key=lambda item: item.name.lower())
    weak_tie_candidates.sort(key=lambda item: item.name.lower())
    bridge_contacts.sort(key=lambda item: item.name.lower())
    isolated_contacts.sort(key=lambda item: item.name.lower())

    return NetworkGraphInsights(
        total_contacts=len(contacts),
        network_density_estimate=density,
        centrality_scores=centrality_scores,
        weak_tie_candidates=weak_tie_candidates,
        strong_tie_contacts=strong_tie_contacts,
        bridge_contacts=bridge_contacts,
        isolated_contacts=isolated_contacts,
        clusters=clusters,
        created_at=_utcnow(),
    )
