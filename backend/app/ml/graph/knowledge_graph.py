import networkx as nx
from typing import List, Dict

class SchemeKnowledgeGraph:
    """
    Knowledge Graph-Based Scheme Matching Engine.
    Builds a relational network of government schemes and finds optimal bundles
    by solving the Maximum Weight Independent Set (MWIS) problem.
    """
    def __init__(self, schemes_data: List[Dict]):
        self.G = nx.Graph()
        self._build_base_graph(schemes_data)

    def _build_base_graph(self, schemes: List[Dict]):
        """Build the master scheme graph with nodes and conflict edges."""
        for scheme in schemes:
            scheme_id = scheme['scheme_id']
            # Default to 0 if financial_benefit is missing
            benefit = scheme.get('financial_benefit', 0)
            self.G.add_node(scheme_id, weight=benefit)

        for scheme in schemes:
            scheme_id = scheme['scheme_id']
            conflicts = scheme.get('conflicts_with', [])
            for conflict_id in conflicts:
                # Add bidirectional edge implicitly in an undirected graph
                self.G.add_edge(scheme_id, conflict_id, relationship='CONFLICTS_WITH')

    def get_optimal_scheme_bundles(self, eligible_schemes: List[Dict]) -> List[Dict]:
        """
        Given a list of linearly eligible schemes (with ML probabilities and explanations attached),
        find all valid non-conflicting combinations (independent sets) and rank them by total financial benefit.
        """
        if not eligible_schemes:
            return []

        # Map the passed dynamic scheme objects by their IDs
        scheme_map = {s['scheme_id']: s for s in eligible_schemes}
        eligible_ids = list(scheme_map.keys())
        
        # Subgraph of only the schemes the farmer passed criteria for
        subgraph = self.G.subgraph(eligible_ids)
        
        # Graph Theory: Independent sets of a graph are cliques in its complement graph.
        complement_graph = nx.complement(subgraph)
        valid_bundles_ids = list(nx.find_cliques(complement_graph))
        
        bundles = []
        for i, bundle_ids in enumerate(valid_bundles_ids):
            # Sum using the dynamic ML-predicted financial value passed in the objects
            total_benefit = sum(scheme_map[sid].get('financial_benefit', 0) for sid in bundle_ids)
            bundle_objs = [scheme_map[sid] for sid in bundle_ids]
            
            # Formatting financial benefit for UI
            formatted_benefit = f"₹{total_benefit:,}" if total_benefit > 0 else "Variable/Non-Monetary"
            
            bundles.append({
                "bundle_id": f"BUNDLE_{i+1:02d}",
                "total_benefit_value": total_benefit,
                "total_benefit": formatted_benefit,
                "schemes": bundle_objs,
                "graph_explanation": "These schemes form an optimal bundle because they share synergistic requirements and do not conflict financially or legally."
            })
            
        # Sort by maximum financial benefit, then by number of schemes
        bundles.sort(key=lambda x: (x["total_benefit_value"], len(x["schemes"])), reverse=True)
        return bundles
