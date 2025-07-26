"""Report generation tool for pandas migration results."""

from typing import Dict, Any, Optional
from ..report_generator import MigrationReportGenerator


class ReportTool:
    """Tool for generating migration reports."""
    
    name = "generate_migration_report"
    description = "Generate comprehensive migration report"
    
    def __init__(self, agent):
        """Initialize the report tool.
        
        Args:
            agent: Parent PandasMigrationAgent instance
        """
        self.agent = agent
        self.report_generator = MigrationReportGenerator()
    
    def __call__(self, 
                 format: str = 'markdown',
                 output_path: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Generate migration report.
        
        Args:
            format: Report format (markdown, html, json)
            output_path: Optional path to save report
            **kwargs: Additional options
            
        Returns:
            Dictionary with report details
        """
        # Get migration state from agent
        migration_state = self.agent.migration_state
        
        # Generate report
        report_content = self.report_generator.generate_report(
            migration_state, format
        )
        
        result = {
            'format': format,
            'content_length': len(report_content),
            'output_path': None,
            'status': 'success'
        }
        
        # Save report if path provided
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                result['output_path'] = output_path
            except Exception as e:
                result['status'] = 'failed'
                result['error'] = str(e)
        
        # Store report content in result if requested
        if kwargs.get('include_content', False):
            result['content'] = report_content
        
        return result
    
    def generate_summary(self, **kwargs) -> str:
        """Generate a brief summary of migration results.
        
        Returns:
            Summary string
        """
        state = self.agent.migration_state
        
        total_files = len(state.get('migration_results', {}))
        successful = sum(1 for r in state.get('migration_results', {}).values() 
                        if r.get('status') == 'success')
        failed = total_files - successful
        
        test_before = state.get('test_results', {}).get('before', {})
        test_after = state.get('test_results', {}).get('after', {})
        
        summary = f"""Migration Summary:
- Files processed: {total_files}
- Successful: {successful}
- Failed: {failed}
- Tests before: {test_before.get('passed', 0)}/{test_before.get('total_tests', 0)} passed
- Tests after: {test_after.get('passed', 0)}/{test_after.get('total_tests', 0)} passed
"""
        
        return summary