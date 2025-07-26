"""Analysis tool for identifying pandas usage and deprecated features."""

from typing import Dict, List, Any
from ..utils import find_python_files, analyze_pandas_usage
from ..compatibility_checker import CompatibilityChecker


class AnalyzeTool:
    """Tool for analyzing repository for pandas usage and compatibility issues."""
    
    name = "analyze_pandas_usage"
    description = "Analyze repository for pandas usage and identify deprecated features"
    
    def __init__(self, agent):
        """Initialize the analysis tool.
        
        Args:
            agent: Parent PandasMigrationAgent instance
        """
        self.agent = agent
        self.compatibility_checker = CompatibilityChecker()
    
    def __call__(self, repo_path: str, **kwargs) -> Dict[str, Any]:
        """Analyze repository for pandas usage.
        
        Args:
            repo_path: Path to repository to analyze
            **kwargs: Additional options
            
        Returns:
            Dictionary with analysis results
        """
        results = {
            'repo_path': repo_path,
            'python_files': [],
            'pandas_files': [],
            'deprecated_features': {},
            'compatibility_issues': {},
            'summary': {}
        }
        
        # Find all Python files
        python_files = find_python_files(repo_path)
        results['python_files'] = python_files
        
        # Analyze each file
        total_deprecated = 0
        total_issues = 0
        
        for file_path in python_files:
            # Analyze pandas usage
            usage = analyze_pandas_usage(file_path)
            
            if usage['imports']['pandas'] or usage['imports']['pandas_modules']:
                results['pandas_files'].append(file_path)
                
                # Check for deprecated features
                if usage['deprecated_features']:
                    results['deprecated_features'][file_path] = usage['deprecated_features']
                    total_deprecated += len(usage['deprecated_features'])
                
                # Check compatibility
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                issues = self.compatibility_checker.check_file(file_path, content)
                if issues:
                    results['compatibility_issues'][file_path] = [
                        {
                            'level': issue.level.value,
                            'category': issue.category,
                            'description': issue.description,
                            'line': issue.line_number,
                            'suggestion': issue.suggestion
                        }
                        for issue in issues
                    ]
                    total_issues += len(issues)
        
        # Generate summary
        results['summary'] = {
            'total_python_files': len(python_files),
            'files_using_pandas': len(results['pandas_files']),
            'files_with_deprecated_features': len(results['deprecated_features']),
            'total_deprecated_features': total_deprecated,
            'files_with_compatibility_issues': len(results['compatibility_issues']),
            'total_compatibility_issues': total_issues
        }
        
        return results