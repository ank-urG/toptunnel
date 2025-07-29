#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AST-based Dependency Analyzer for tracking imports of aqr.core.panel
A simpler, more reliable alternative using Python's AST module
Compatible with Python 3.6+
"""

import ast
import os
import sys
from pathlib import Path
from collections import defaultdict, deque
import json
import logging

# Visualization imports
try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    print("Please install: pip install networkx matplotlib")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract import statements"""
    
    def __init__(self):
        self.imports = []
        self.from_imports = []
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            if node.names[0].name == '*':
                self.from_imports.append(node.module)
            else:
                for alias in node.names:
                    full_name = f"{node.module}.{alias.name}"
                    self.from_imports.append(full_name)
                self.from_imports.append(node.module)
        self.generic_visit(node)


class SimpleDepAnalyzer:
    """Simple AST-based dependency analyzer"""
    
    def __init__(self, workspace_path, source_repo, target_module='aqr.core.panel'):
        self.workspace_path = Path(workspace_path).resolve()
        self.source_repo = source_repo
        self.target_module = target_module
        self.repos = self._find_repos()
        self.import_graph = defaultdict(set)  # module -> set of imported modules
        self.module_to_file = {}  # module name -> file path
        self.module_to_repo = {}  # module name -> repo name
        self.paths_to_target = []
    
    def _find_repos(self):
        """Find all Python repositories in workspace"""
        repos = {}
        for item in self.workspace_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if any(item.rglob('*.py')):
                    repos[item.name] = item
                    logger.info(f"Found repository: {item.name}")
        return repos
    
    def _get_module_name(self, file_path, repo_path):
        """Convert file path to module name"""
        try:
            relative_path = file_path.relative_to(repo_path)
            parts = list(relative_path.parts)
            
            if parts[-1] == '__init__.py':
                parts = parts[:-1]
            elif parts[-1].endswith('.py'):
                parts[-1] = parts[-1][:-3]
            
            return '.'.join(parts) if parts else None
        except ValueError:
            return None
    
    def _analyze_file(self, file_path, repo_name):
        """Analyze a single Python file for imports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            visitor = ImportVisitor()
            visitor.visit(tree)
            
            # Get module name for this file
            module_name = self._get_module_name(file_path, self.repos[repo_name])
            if not module_name:
                return
            
            full_module_name = f"{repo_name}.{module_name}" if module_name else repo_name
            
            self.module_to_file[full_module_name] = file_path
            self.module_to_repo[full_module_name] = repo_name
            
            # Process imports
            all_imports = visitor.imports + visitor.from_imports
            for imp in all_imports:
                # Check if import is aqr.core.panel or might lead to it
                if imp == self.target_module or imp.startswith(self.target_module.split('.')[0]):
                    self.import_graph[full_module_name].add(imp)
                
                # Check if import is from another repo in workspace
                for other_repo in self.repos:
                    if imp.startswith(other_repo):
                        self.import_graph[full_module_name].add(imp)
            
            return full_module_name, all_imports
            
        except Exception as e:
            logger.debug(f"Error analyzing {file_path}: {e}")
            return None, []
    
    def analyze(self):
        """Analyze all Python files in all repos"""
        logger.info("Starting dependency analysis...")
        
        # First pass: analyze all files
        for repo_name, repo_path in self.repos.items():
            logger.info(f"Analyzing repository: {repo_name}")
            py_files = list(repo_path.rglob('*.py'))
            
            for py_file in py_files:
                self._analyze_file(py_file, repo_name)
        
        # Second pass: build complete import graph
        # This handles transitive dependencies
        self._build_complete_graph()
        
        # Find paths to target
        self._find_paths_to_target()
        
        logger.info(f"Analysis complete. Found {len(self.paths_to_target)} paths to {self.target_module}")
    
    def _build_complete_graph(self):
        """Build complete dependency graph including transitive dependencies"""
        # Add nodes for all known modules
        all_modules = set(self.import_graph.keys())
        for imports in self.import_graph.values():
            all_modules.update(imports)
        
        # Ensure target module is in the graph
        if self.target_module not in all_modules:
            logger.warning(f"Target module '{self.target_module}' not found in imports")
    
    def _find_paths_to_target(self):
        """Find all paths from source repo to target module using BFS"""
        # Get all modules from source repo
        source_modules = [
            module for module, repo in self.module_to_repo.items()
            if repo == self.source_repo
        ]
        
        if not source_modules:
            logger.warning(f"No modules found in source repo '{self.source_repo}'")
            return
        
        # BFS to find all paths
        for start_module in source_modules:
            paths = self._bfs_paths(start_module, self.target_module)
            self.paths_to_target.extend(paths)
    
    def _bfs_paths(self, start, target, max_depth=10):
        """Find all paths from start to target using BFS"""
        if start == target:
            return [[start]]
        
        paths = []
        queue = deque([(start, [start])])
        visited = set()
        
        while queue:
            node, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if node in visited:
                continue
            
            visited.add(node)
            
            for neighbor in self.import_graph.get(node, []):
                if neighbor == target:
                    paths.append(path + [neighbor])
                elif neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
        
        return paths
    
    def visualize(self, output_file='ast_dependency_graph.png'):
        """Create visualization of dependency paths"""
        if not self.paths_to_target:
            logger.warning("No paths to visualize")
            return
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add all nodes and edges from paths
        for path in self.paths_to_target:
            for i in range(len(path) - 1):
                G.add_edge(path[i], path[i + 1])
        
        # Set up the plot
        plt.figure(figsize=(20, 14))
        
        # Calculate layout
        if len(G) < 50:
            pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
        else:
            # For larger graphs, use hierarchical layout
            pos = nx.nx_pydot.graphviz_layout(G, prog='dot') if hasattr(nx, 'nx_pydot') else nx.spring_layout(G)
        
        # Color nodes by repository
        node_colors = []
        repo_color_map = {
            repo: plt.cm.Set3(i) 
            for i, repo in enumerate(self.repos.keys())
        }
        
        for node in G.nodes():
            if node == self.target_module:
                node_colors.append('#FF0000')  # Red for target
            else:
                repo = self.module_to_repo.get(node, 'external')
                if repo in repo_color_map:
                    node_colors.append(repo_color_map[repo])
                else:
                    node_colors.append('#CCCCCC')  # Gray for external
        
        # Node sizes
        node_sizes = []
        for node in G.nodes():
            if node == self.target_module:
                node_sizes.append(3000)
            elif any(node == path[0] for path in self.paths_to_target):
                node_sizes.append(2000)
            else:
                node_sizes.append(1000)
        
        # Draw the graph
        nx.draw_networkx_nodes(
            G, pos,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.8,
            edgecolors='black',
            linewidths=2
        )
        
        nx.draw_networkx_edges(
            G, pos,
            edge_color='gray',
            arrows=True,
            arrowsize=20,
            alpha=0.6,
            width=2,
            arrowstyle='->'
        )
        
        # Labels
        labels = {}
        for node in G.nodes():
            if node == self.target_module:
                labels[node] = f"TARGET:\n{node}"
            else:
                # Shorten long module names
                parts = node.split('.')
                if len(parts) > 3:
                    labels[node] = f"{parts[0]}...{parts[-1]}"
                else:
                    labels[node] = node
        
        nx.draw_networkx_labels(
            G, pos, labels,
            font_size=10,
            font_weight='bold',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7)
        )
        
        # Create legend
        legend_patches = []
        for repo, color in repo_color_map.items():
            legend_patches.append(mpatches.Patch(color=color, label=repo))
        legend_patches.append(mpatches.Patch(color='#FF0000', label=f'Target: {self.target_module}'))
        legend_patches.append(mpatches.Patch(color='#CCCCCC', label='External'))
        
        plt.legend(handles=legend_patches, loc='upper left', bbox_to_anchor=(1, 1))
        
        # Title and cleanup
        plt.title(
            f"Dependency Paths from '{self.source_repo}' to '{self.target_module}'\\n"
            f"Found {len(self.paths_to_target)} paths",
            fontsize=16,
            fontweight='bold'
        )
        
        plt.axis('off')
        plt.tight_layout()
        
        # Save
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"Visualization saved to {output_file}")
        plt.show()
    
    def save_results(self, output_file='ast_analysis_results.json'):
        """Save analysis results to JSON"""
        results = {
            'source_repo': self.source_repo,
            'target_module': self.target_module,
            'workspace_path': str(self.workspace_path),
            'repositories_found': list(self.repos.keys()),
            'total_paths_found': len(self.paths_to_target),
            'paths': [
                {
                    'path': path,
                    'length': len(path),
                    'start_module': path[0],
                    'repos_involved': list(set(
                        self.module_to_repo.get(m, 'external') for m in path
                    ))
                }
                for path in sorted(self.paths_to_target, key=len)[:20]  # Show top 20 shortest paths
            ],
            'direct_importers': sorted(list(set(
                path[-2] for path in self.paths_to_target 
                if len(path) == 2
            ))),
            'all_importers': sorted(list(set(
                path[-2] for path in self.paths_to_target 
                if len(path) >= 2
            )))
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"DEPENDENCY ANALYSIS SUMMARY")
        print(f"{'='*70}")
        print(f"Workspace: {self.workspace_path}")
        print(f"Source Repository: {self.source_repo}")
        print(f"Target Module: {self.target_module}")
        print(f"Total Repositories: {len(self.repos)}")
        print(f"Total Paths Found: {len(self.paths_to_target)}")
        
        if self.paths_to_target:
            print(f"\nPath Lengths:")
            path_lengths = [len(p) for p in self.paths_to_target]
            print(f"  - Shortest: {min(path_lengths)}")
            print(f"  - Longest: {max(path_lengths)}")
            print(f"  - Average: {sum(path_lengths)/len(path_lengths):.1f}")
            
            print(f"\nDirect Importers ({len(results['direct_importers'])}):")
            for imp in results['direct_importers'][:5]:
                print(f"  - {imp}")
            if len(results['direct_importers']) > 5:
                print(f"  ... and {len(results['direct_importers']) - 5} more")
            
            print(f"\nExample Shortest Paths:")
            for i, path_info in enumerate(results['paths'][:3]):
                print(f"\n  Path {i+1} (length {path_info['length']}):")
                for j, module in enumerate(path_info['path']):
                    print(f"    {'→ ' if j > 0 else ''}{module}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze Python dependencies using AST parsing'
    )
    parser.add_argument('workspace', help='Path to workspace directory')
    parser.add_argument('source_repo', help='Name of source repository')
    parser.add_argument(
        '--target', 
        default='aqr.core.panel',
        help='Target module to track (default: aqr.core.panel)'
    )
    parser.add_argument(
        '--output-image',
        default='ast_dependency_graph.png',
        help='Output image file'
    )
    parser.add_argument(
        '--output-json',
        default='ast_analysis_results.json',
        help='Output JSON file'
    )
    
    args = parser.parse_args()
    
    # Run analysis
    analyzer = SimpleDepAnalyzer(args.workspace, args.source_repo, args.target)
    analyzer.analyze()
    analyzer.visualize(args.output_image)
    analyzer.save_results(args.output_json)


if __name__ == '__main__':
    main()
