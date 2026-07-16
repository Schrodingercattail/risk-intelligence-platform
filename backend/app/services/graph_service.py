"""
Graph Analysis Service

Uses NetworkX to detect suspicious account clusters and relationships.
Service Layer - Independent of API, can be tested standalone.
"""
from typing import Dict, List, Any, Optional
import networkx as nx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.database import Device, User, AccountCluster, ClusterMember, ClusterType


class GraphAnalysisService:
    """
    Graph Analysis Service

    Input: device relationships, trading patterns
    Output: clusters, linked accounts, graph structure

    Uses NetworkX for relationship detection and cluster analysis.
    """

    def __init__(self, db: AsyncSession):
        """Initialize graph service with database session."""
        self.db = db
        self.graph = None

    async def build_device_graph(self) -> nx.Graph:
        """
        Build a graph of user relationships based on shared devices.

        Returns:
            NetworkX graph with users as nodes and shared devices as edges
        """
        # Get all devices with users
        result = await self.db.execute(
            select(Device.device_id, Device.user_id)
        )
        devices = result.all()

        # Build graph
        graph = nx.Graph()

        # Group users by device
        device_users: Dict[str, List[str]] = {}
        for device_id, user_id in devices:
            if device_id:
                if device_id not in device_users:
                    device_users[device_id] = []
                device_users[device_id].append(user_id)

        # Add edges between users sharing devices
        for device_id, users in device_users.items():
            # Add all users as nodes
            for user_id in users:
                graph.add_node(user_id, type="user")

            # Connect all users sharing this device
            for i, user1 in enumerate(users):
                for user2 in users[i + 1:]:
                    if graph.has_edge(user1, user2):
                        # Increment edge weight if already connected
                        graph[user1][user2]["weight"] = graph[user1][user2].get("weight", 1) + 1
                    else:
                        graph.add_edge(user1, user2, type="shared_device", weight=1)

        self.graph = graph
        return graph

    async def build_ip_graph(self) -> nx.Graph:
        """
        Build a graph of user relationships based on shared IP addresses.

        Returns:
            NetworkX graph with users as nodes and shared IPs as edges
        """
        result = await self.db.execute(
            select(Device.ip_address, Device.user_id)
            .where(Device.ip_address.isnot(None))
        )
        ips = result.all()

        graph = nx.Graph()

        # Group users by IP
        ip_users: Dict[str, List[str]] = {}
        for ip_address, user_id in ips:
            if ip_address:
                if ip_address not in ip_users:
                    ip_users[ip_address] = []
                ip_users[ip_address].append(user_id)

        # Add edges between users sharing IPs
        for ip_address, users in ip_users.items():
            for user_id in users:
                graph.add_node(user_id, type="user")

            for i, user1 in enumerate(users):
                for user2 in users[i + 1:]:
                    if graph.has_edge(user1, user2):
                        graph[user1][user2]["weight"] = graph[user1][user2].get("weight", 1) + 1
                    else:
                        graph.add_edge(user1, user2, type="shared_ip", weight=1)

        return graph

    async def detect_device_sharing_clusters(self, min_members: int = 2) -> List[Dict[str, Any]]:
        """
        Detect clusters of users sharing devices.

        Args:
            min_members: Minimum cluster size to report

        Returns:
            List of cluster information dicts
        """
        graph = await self.build_device_graph()

        # Find connected components (clusters)
        clusters = []
        for component in nx.connected_components(graph):
            if len(component) >= min_members:
                members = list(component)
                clusters.append({
                    "members": members,
                    "size": len(members),
                    "detection_type": ClusterType.DEVICE_SHARING.value,
                    "risk_score": self._calculate_cluster_risk_score(members, graph),
                })

        return clusters

    async def detect_all_clusters(self) -> List[AccountCluster]:
        """
        Detect all suspicious clusters and store in database.

        Returns:
            List of created AccountCluster objects
        """
        # Detect device sharing clusters
        device_clusters = await self.detect_device_sharing_clusters()

        stored_clusters = []

        for cluster_info in device_clusters:
            # Create cluster record
            cluster = AccountCluster(
                cluster_name=f"Cluster_{cluster_info['detection_type']}_{len(stored_clusters) + 1}",
                detection_type=cluster_info["detection_type"],
                member_count=cluster_info["size"],
                risk_score=cluster_info["risk_score"],
            )
            self.db.add(cluster)
            await self.db.flush()

            # Add cluster members
            for user_id in cluster_info["members"]:
                member = ClusterMember(
                    cluster_id=cluster.cluster_id,
                    user_id=user_id,
                    role_in_cluster="spoke",  # Will be refined by more sophisticated analysis
                )
                self.db.add(member)

            stored_clusters.append(cluster)

        await self.db.commit()
        return stored_clusters

    async def get_user_graph(self, user_id: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get relationship graph for a specific user.

        Args:
            user_id: User to get graph for
            depth: How many hops to explore

        Returns:
            Dict with nodes and edges for visualization
        """
        graph = await self.build_device_graph()

        if user_id not in graph:
            return {"nodes": [], "edges": []}

        # Get subgraph around user
        nodes = set([user_id])
        edges = []

        # BFS to collect neighbors
        current_level = [user_id]
        visited = set([user_id])

        for _ in range(depth):
            next_level = []
            for node in current_level:
                if node in graph:
                    neighbors = list(graph.neighbors(node))
                    for neighbor in neighbors:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            next_level.append(neighbor)
                            nodes.add(neighbor)

                            # Get edge info
                            edge_data = graph[node][neighbor]
                            edges.append({
                                "source": node,
                                "target": neighbor,
                                "type": edge_data.get("type", "connected"),
                            })

            current_level = next_level
            if not current_level:
                break

        # Format nodes for frontend
        formatted_nodes = []
        for node in nodes:
            # Get user risk level if available
            user = await self.db.get(User, node)
            formatted_nodes.append({
                "id": node,
                "type": "user",
                "risk_level": user.risk_level if user else None,
                "label": node,
            })

        return {
            "nodes": formatted_nodes,
            "edges": edges,
        }

    def _calculate_cluster_risk_score(self, members: List[str], graph: nx.Graph) -> float:
        """
        Calculate risk score for a cluster.

        Args:
            members: List of user IDs in cluster
            graph: NetworkX graph

        Returns:
            Risk score (0-100)
        """
        # Base score on cluster size
        size_score = min(len(members) * 10, 50)

        # Add score based on internal connectivity
        if len(members) >= 2:
            subgraph = graph.subgraph(members)
            density = nx.density(subgraph)
            connectivity_score = density * 30
        else:
            connectivity_score = 0

        total_score = size_score + connectivity_score

        # Add some randomness for demo
        import random
        total_score += random.uniform(0, 20)

        return round(min(total_score, 100), 2)
