#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Deep Dependency Analyzer for tracking all paths to aqr.core.panel
Recursively follows imports across multiple repositories
"""

import ast
import os
import sys
from pathlib import Path
from collections import defaultdict, deque
import json
import logging
from typing import Dict, Set, List, Tuple, Optional

try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
except ImportError:
    print("Please install: pip install networkx matplotlib")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImportVisitor(ast.NodeVisitor):
    """Extract all imports from a Python file"""
    
    def __init__(self, current_module_path=None):
        self.imports = set()
        self.current_module_path = current_module_path
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            # Add the base module
            self.imports.add(node.module)
            
            # For relative imports, we need to resolve them
            if node.level > 0 and self.current_module_path:
                # Handle relative imports like "from . import x" or "from .. import y"
                parts = self.current_module_path.split('.')
                if node.level <= len(parts):
                    base = '.'.join(parts[:-node.level])
                    if base and node.module:
                        full_module = f"{base}.{node.module}"
                        self.imports.add(full_module)
            else:
                # Add each imported name as a potential module
                for alias in node.names:
                    if alias.name != '*':
                        full_name = f"{node.module}.{alias.name}"
                        self.imports.add(full_name)
        self.generic_visit(node)


class DeepDependencyAnalyzer:
    """Recursively analyze dependencies across repositories"""
    
    def __init__(self, workspace_path: str, source_repo: str, target_module: str = 'aqr.core.panel'):
        self.workspace_path = Path(workspace_path).resolve()
        self.source_repo = source_repo
        self.target_module = target_module
        
        # Repository mapping
        self.repos = self._discover_repos()
        if source_repo not in self.repos:
            raise ValueError(f"Source repo '{source_repo}' not found in workspace")
        
        # Module mappings
        self.module_to_file: Dict[str, Path] = {}
        self.file_to_module: Dict[Path, str] = {}
        self.module_to_repo: Dict[str, str] = {}
        
        # Import graph
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # Who imports this module
        
        # Analysis results
        self.all_paths: List[List[str]] = []
        self.module_hierarchy: Dict[str, List] = defaultdict(list)
        
        # Cache for analyzed modules
        self.analyzed_modules: Set[str] = set()
        self.module_exists: Dict[str, bool] = {}
    
    def _discover_repos(self) -> Dict[str, Path]:
        """Discover all Python repositories in workspace"""
        repos = {}
        logger.info(f"Scanning workspace: {self.workspace_path}")
        
        for item in self.workspace_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it contains Python files
                py_files = list(item.rglob('*.py'))
                if py_files:
                    repos[item.name] = item
                    logger.info(f"Found repository: {item.name} ({len(py_files)} Python files)")
        
        return repos
    
    def _build_module_mappings(self):
        """Build mappings between modules, files, and repos"""
        logger.info("Building module mappings...")
        
        for repo_name, repo_path in self.repos.items():
            # Find all Python files
            for py_file in repo_path.rglob('*.py'):
                # Skip test files if needed
                if '__pycache__' in str(py_file):
                    continue
                
                # Convert file path to module name
                try:
                    rel_path = py_file.relative_to(repo_path)
                    parts = list(rel_path.parts)
                    
                    # Handle __init__.py
                    if parts[-1] == '__init__.py':
                        parts = parts[:-1]
                    elif parts[-1].endswith('.py'):
                        parts[-1] = parts[-1][:-3]
                    
                    # Create module name
                    if parts:
                        module_name = repo_name + '.' + '.'.join(parts)
                    else:
                        module_name = repo_name
                    
                    # Store mappings
                    self.module_to_file[module_name] = py_file
                    self.file_to_module[py_file] = module_name
                    self.module_to_repo[module_name] = repo_name
                    self.module_exists[module_name] = True
                    
                except Exception as e:
                    logger.debug(f"Error processing {py_file}: {e}")
        
        logger.info(f"Found {len(self.module_to_file)} Python modules across all repos")
    
    def _resolve_import(self, import_name: str, importing_module: str) -> Optional[str]:
        """Resolve an import name to a full module path"""
        # Direct match
        if import_name in self.module_exists:
            return import_name
        
        # Check if it's a submodule of any repo
        for repo_name in self.repos:
            if import_name.startswith(repo_name + '.'):
                # Check if the module exists
                if import_name in self.module_exists:
                    return import_name
                
                # Check if it's a package (has __init__.py)
                potential_package = import_name
                while '.' in potential_package:
                    if potential_package in self.module_exists:
                        return potential_package
                    potential_package = '.'.join(potential_package.split('.')[:-1])
        
        # Check if it's the target module
        if import_name == self.target_module or import_name.startswith(self.target_module):
            return self.target_module
        
        return None
    
    def _analyze_module(self, module_name: str) -> Set[str]:
        """Analyze a module and return its imports"""
        if module_name in self.analyzed_modules:
            return self.import_graph.get(module_name, set())
        
        self.analyzed_modules.add(module_name)
        
        if module_name not in self.module_to_file:
            return set()
        
        file_path = self.module_to_file[module_name]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            visitor = ImportVisitor(module_name)
            visitor.visit(tree)
            
            # Resolve imports
            resolved_imports = set()
            for imp in visitor.imports:
                resolved = self._resolve_import(imp, module_name)
                if resolved:
                    resolved_imports.add(resolved)
                    # Check if this is our target
                    if resolved == self.target_module or self.target_module in resolved:
                        logger.info(f"Found import of {self.target_module} in {module_name}")
            
            # Update graphs
            self.import_graph[module_name] = resolved_imports
            for imp in resolved_imports:
                self.reverse_graph[imp].add(module_name)
            
            return resolved_imports
            
        except Exception as e:
            logger.debug(f"Error analyzing {module_name}: {e}")
            return set()
    
    def _recursive_analyze(self, start_modules: List[str], max_depth: int = 10):
        """Recursively analyze imports starting from given modules"""
        to_analyze = deque([(m, 0) for m in start_modules])
        
        while to_analyze:
            module, depth = to_analyze.popleft()
            
            if depth > max_depth:
                continue
            
            imports = self._analyze_module(module)
            
            for imp in imports:
                if imp not in self.analyzed_modules:
                    to_analyze.append((imp, depth + 1))
    
    def analyze(self):
        """Perform complete dependency analysis"""
        logger.info("Starting deep dependency analysis...")
        
        # Build module mappings
        self._build_module_mappings()
        
        # Get all modules from source repo
        source_modules = [
            module for module, repo in self.module_to_repo.items()
            if repo == self.source_repo
        ]
        
        logger.info(f"Found {len(source_modules)} modules in {self.source_repo}")
        
        # Recursively analyze all imports
        self._recursive_analyze(source_modules)
        
        # Find all paths to target
        self._find_all_paths()
        
        # Build hierarchy
        self._build_hierarchy()
        
        logger.info(f"Analysis complete. Found {len(self.all_paths)} paths to {self.target_module}")
    
    def _find_all_paths(self):
        """Find all paths from source repo to target module"""
        logger.info("Finding all paths to target module...")
        
        # Check if target module is in our graph
        if self.target_module not in self.reverse_graph and self.target_module not in self.import_graph:
            logger.warning(f"Target module {self.target_module} not found in any imports!")
            return
        
        # Get all source modules
        source_modules = [
            module for module, repo in self.module_to_repo.items()
            if repo == self.source_repo
        ]
        
        # Find paths using DFS
        for source in source_modules:
            paths = self._dfs_paths(source, self.target_module)
            self.all_paths.extend(paths)
        
        # Remove duplicates
        unique_paths = []
        seen = set()
        for path in self.all_paths:
            path_tuple = tuple(path)
            if path_tuple not in seen:
                seen.add(path_tuple)
                unique_paths.append(path)
        
        self.all_paths = unique_paths
    
    def _dfs_paths(self, start: str, target: str, visited: Set[str] = None, path: List[str] = None) -> List[List[str]]:
        """Find all paths using DFS"""
        if visited is None:
            visited = set()
        if path is None:
            path = []
        
        path = path + [start]
        visited.add(start)
        
        if start == target:
            return [path]
        
        if len(path) > 15:  # Prevent infinite loops
            return []
        
        paths = []
        
        for neighbor in self.import_graph.get(start, set()):
            if neighbor not in visited:
                if neighbor == target or target in neighbor:
                    paths.append(path + [neighbor])
                else:
                    newpaths = self._dfs_paths(neighbor, target, visited.copy(), path)
                    paths.extend(newpaths)
        
        return paths
    
    def _build_hierarchy(self):
        """Build hierarchical structure of paths"""
        for path in self.all_paths:
            if path:
                self.module_hierarchy[path[0]].append(path)
    
    def export_hierarchy(self, output_file: str = 'import_hierarchy.md'):
        """Export hierarchical structure to markdown"""
        logger.info(f"Exporting hierarchy to {output_file}")
        
        with open(output_file, 'w') as f:
            f.write(f"# Import Hierarchy Analysis\n\n")
            f.write(f"**Target Module:** `{self.target_module}`\n")
            f.write(f"**Source Repository:** `{self.source_repo}`\n")
            f.write(f"**Total Paths Found:** {len(self.all_paths)}\n\n")
            
            # Group paths by source file
            for source_module in sorted(self.module_hierarchy.keys()):
                repo = self.module_to_repo.get(source_module, 'unknown')
                f.write(f"## {source_module}\n")
                f.write(f"*Repository: {repo}*\n\n")
                
                paths = self.module_hierarchy[source_module]
                for i, path in enumerate(paths, 1):
                    f.write(f"### Path {i} (Length: {len(path)})\n\n")
                    f.write("```\n")
                    for j, module in enumerate(path):
                        indent = "  " * j
                        module_repo = self.module_to_repo.get(module, 'external')
                        if module == self.target_module:
                            f.write(f"{indent}└─> {module} [TARGET]\n")
                        else:
                            f.write(f"{indent}└─> {module} [{module_repo}]\n")
                    f.write("```\n\n")
            
            # Summary section
            f.write("## Summary\n\n")
            
            # Direct importers
            direct_importers = set()
            for path in self.all_paths:
                if len(path) == 2:
                    direct_importers.add(path[0])
            
            if direct_importers:
                f.write(f"### Direct Importers ({len(direct_importers)})\n\n")
                for imp in sorted(direct_importers):
                    f.write(f"- `{imp}`\n")
                f.write("\n")
            
            # Repos involved
            repos_involved = set()
            for path in self.all_paths:
                for module in path:
                    repo = self.module_to_repo.get(module, 'external')
                    if repo != 'external':
                        repos_involved.add(repo)
            
            f.write(f"### Repositories Involved ({len(repos_involved)})\n\n")
            for repo in sorted(repos_involved):
                f.write(f"- {repo}\n")
    
    def export_json(self, output_file: str = 'import_hierarchy.json'):
        """Export results to JSON"""
        results = {
            'target_module': self.target_module,
            'source_repository': self.source_repo,
            'total_paths': len(self.all_paths),
            'paths': [
                {
                    'source': path[0],
                    'target': path[-1],
                    'length': len(path),
                    'modules': path,
                    'repos_involved': list(set(
                        self.module_to_repo.get(m, 'external') for m in path
                    ))
                }
                for path in self.all_paths
            ],
            'module_hierarchy': {
                source: [
                    {
                        'path': path,
                        'length': len(path)
                    }
                    for path in paths
                ]
                for source, paths in self.module_hierarchy.items()
            },
            'statistics': {
                'total_modules_analyzed': len(self.analyzed_modules),
                'modules_importing_target': len(self.reverse_graph.get(self.target_module, set())),
                'shortest_path_length': min(len(p) for p in self.all_paths) if self.all_paths else 0,
                'longest_path_length': max(len(p) for p in self.all_paths) if self.all_paths else 0,
                'average_path_length': sum(len(p) for p in self.all_paths) / len(self.all_paths) if self.all_paths else 0
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Exported JSON results to {output_file}")
    
    def visualize(self, output_file: str = 'dependency_graph.png', max_nodes: int = 100):
        """Create comprehensive visualization"""
        logger.info("Creating visualization...")
        
        # Create graph from all paths
        G = nx.DiGraph()
        
        # Add all edges from paths
        edge_counts = defaultdict(int)
        for path in self.all_paths:
            for i in range(len(path) - 1):
                G.add_edge(path[i], path[i + 1])
                edge_counts[(path[i], path[i + 1])] += 1
        
        # If graph is too large, filter to most important nodes
        if len(G) > max_nodes:
            logger.warning(f"Graph has {len(G)} nodes, filtering to {max_nodes} most important")
            # Calculate importance based on centrality
            centrality = nx.betweenness_centrality(G)
            important_nodes = sorted(centrality.keys(), key=lambda x: centrality[x], reverse=True)[:max_nodes]
            
            # Always include target and source modules
            important_nodes = set(important_nodes)
            important_nodes.add(self.target_module)
            for module in self.module_hierarchy.keys():
                important_nodes.add(module)
            
            G = G.subgraph(important_nodes).copy()
        
        # Create layout
        plt.figure(figsize=(24, 18))
        
        # Use hierarchical layout
        layers = self._create_layers(G)
        pos = self._hierarchical_layout(layers)
        
        # Color mapping
        repo_colors = {
            repo: plt.cm.Set3(i % 12)
            for i, repo in enumerate(self.repos.keys())
        }
        
        # Node properties
        node_colors = []
        node_sizes = []
        node_shapes = []
        
        for node in G.nodes():
            # Color
            if node == self.target_module:
                node_colors.append('#FF0000')  # Red for target
                node_sizes.append(3000)
            elif node in self.module_hierarchy:
                node_colors.append('#00FF00')  # Green for source modules
                node_sizes.append(2500)
            else:
                repo = self.module_to_repo.get(node, 'external')
                if repo in repo_colors:
                    node_colors.append(repo_colors[repo])
                else:
                    node_colors.append('#CCCCCC')
                node_sizes.append(1500)
        
        # Draw nodes
        nx.draw_networkx_nodes(
            G, pos,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.9,
            edgecolors='black',
            linewidths=2
        )
        
        # Draw edges with varying widths based on path count
        edge_widths = []
        for edge in G.edges():
            count = edge_counts.get(edge, 1)
            edge_widths.append(min(count * 0.5 + 1, 5))
        
        nx.draw_networkx_edges(
            G, pos,
            edge_color='gray',
            width=edge_widths,
            alpha=0.6,
            arrows=True,
            arrowsize=20,
            arrowstyle='-|>',
            connectionstyle="arc3,rad=0.1"
        )
        
        # Labels
        labels = {}
        for node in G.nodes():
            if node == self.target_module:
                labels[node] = f"TARGET:\n{node}"
            elif node in self.module_hierarchy:
                labels[node] = f"SOURCE:\n{node.split('.')[-1]}"
            else:
                # Shorten module names
                parts = node.split('.')
                if len(parts) > 3:
                    labels[node] = f"{parts[0]}...{parts[-1]}"
                else:
                    labels[node] = node
        
        nx.draw_networkx_labels(
            G, pos, labels,
            font_size=9,
            font_weight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', edgecolor='black', alpha=0.8)
        )
        
        # Legend
        legend_elements = []
        legend_elements.append(mpatches.Patch(color='#FF0000', label=f'Target: {self.target_module}'))
        legend_elements.append(mpatches.Patch(color='#00FF00', label=f'Source modules'))
        for repo, color in sorted(repo_colors.items()):
            if any(self.module_to_repo.get(n) == repo for n in G.nodes()):
                legend_elements.append(mpatches.Patch(color=color, label=repo))
        legend_elements.append(mpatches.Patch(color='#CCCCCC', label='External'))
        
        plt.legend(handles=legend_elements, loc='upper left', fontsize=10)
        
        # Title and info
        plt.title(
            f"Deep Dependency Analysis: {self.source_repo} → {self.target_module}\n"
            f"Showing {len(G)} modules, {len(self.all_paths)} total paths found",
            fontsize=16,
            fontweight='bold'
        )
        
        # Add text box with statistics
        stats_text = f"Total Paths: {len(self.all_paths)}\n"
        if self.all_paths:
            stats_text += f"Shortest Path: {min(len(p) for p in self.all_paths)}\n"
            stats_text += f"Longest Path: {max(len(p) for p in self.all_paths)}\n"
            stats_text += f"Avg Path Length: {sum(len(p) for p in self.all_paths) / len(self.all_paths):.1f}"
        
        plt.text(0.02, 0.02, stats_text,
                transform=plt.gca().transAxes,
                bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.8),
                fontsize=10,
                verticalalignment='bottom')
        
        plt.axis('off')
        plt.tight_layout()
        
        # Save
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"Visualization saved to {output_file}")
        plt.show()
    
    def _create_layers(self, G):
        """Create layers for hierarchical layout"""
        layers = defaultdict(list)
        
        # Start with source modules
        current_layer = [n for n in self.module_hierarchy.keys() if n in G]
        layer_num = 0
        visited = set(current_layer)
        layers[layer_num] = current_layer
        
        # BFS to create layers
        while current_layer:
            next_layer = []
            for node in current_layer:
                for successor in G.successors(node):
                    if successor not in visited:
                        next_layer.append(successor)
                        visited.add(successor)
            
            if next_layer:
                layer_num += 1
                layers[layer_num] = next_layer
                current_layer = next_layer
            else:
                break
        
        # Add any remaining nodes
        for node in G.nodes():
            if node not in visited:
                layers[layer_num + 1].append(node)
        
        return layers
    
    def _hierarchical_layout(self, layers):
        """Create hierarchical layout from layers"""
        pos = {}
        
        for layer_num, nodes in layers.items():
            y = -layer_num * 3
            x_spacing = 4.0
            total_width = len(nodes) * x_spacing
            x_start = -total_width / 2
            
            for i, node in enumerate(nodes):
                x = x_start + i * x_spacing
                pos[node] = (x, y)
        
        return pos


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Deep dependency analysis with recursive import tracking'
    )
    parser.add_argument('workspace', help='Path to workspace directory')
    parser.add_argument('source_repo', help='Name of source repository')
    parser.add_argument(
        '--target', 
        default='aqr.core.panel',
        help='Target module to track (default: aqr.core.panel)'
    )
    parser.add_argument(
        '--output-md',
        default='import_hierarchy.md',
        help='Output markdown file for hierarchy'
    )
    parser.add_argument(
        '--output-json',
        default='import_hierarchy.json',
        help='Output JSON file'
    )
    parser.add_argument(
        '--output-graph',
        default='dependency_graph.png',
        help='Output graph visualization'
    )
    parser.add_argument(
        '--max-nodes',
        type=int,
        default=100,
        help='Maximum nodes to show in visualization'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Run analysis
        analyzer = DeepDependencyAnalyzer(
            args.workspace,
            args.source_repo,
            args.target
        )
        
        analyzer.analyze()
        
        # Export results
        analyzer.export_hierarchy(args.output_md)
        analyzer.export_json(args.output_json)
        analyzer.visualize(args.output_graph, args.max_nodes)
        
        # Print summary
        print(f"\n{'='*70}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*70}")
        print(f"Workspace: {args.workspace}")
        print(f"Source Repository: {args.source_repo}")
        print(f"Target Module: {args.target}")
        print(f"\nResults:")
        print(f"  - Total paths found: {len(analyzer.all_paths)}")
        print(f"  - Modules analyzed: {len(analyzer.analyzed_modules)}")
        print(f"  - Direct importers: {len(analyzer.reverse_graph.get(args.target, set()))}")
        print(f"\nOutput files:")
        print(f"  - Hierarchy (Markdown): {args.output_md}")
        print(f"  - Full results (JSON): {args.output_json}")
        print(f"  - Visualization (PNG): {args.output_graph}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
