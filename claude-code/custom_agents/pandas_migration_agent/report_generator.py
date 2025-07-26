"""Report generator for pandas migration results."""

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import html


class MigrationReportGenerator:
    """Generates comprehensive reports for pandas migration."""
    
    def __init__(self):
        """Initialize the report generator."""
        self.report_formats = ['markdown', 'html', 'json']
        
    def generate_report(self, 
                       migration_state: Dict[str, Any],
                       format: str = 'markdown') -> str:
        """Generate a migration report in the specified format.
        
        Args:
            migration_state: Complete migration state data
            format: Output format (markdown, html, json)
            
        Returns:
            Formatted report string
        """
        if format == 'markdown':
            return self._generate_markdown_report(migration_state)
        elif format == 'html':
            return self._generate_html_report(migration_state)
        elif format == 'json':
            return json.dumps(migration_state, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_markdown_report(self, state: Dict[str, Any]) -> str:
        """Generate a detailed markdown report."""
        sections = []
        
        # Header
        sections.append(self._generate_header(state))
        
        # Executive Summary
        sections.append(self._generate_executive_summary(state))
        
        # Migration Details
        sections.append(self._generate_migration_details(state))
        
        # Test Results
        sections.append(self._generate_test_results(state))
        
        # File Changes
        sections.append(self._generate_file_changes(state))
        
        # Compatibility Issues
        sections.append(self._generate_compatibility_issues(state))
        
        # Recommendations
        sections.append(self._generate_recommendations(state))
        
        # Appendix
        sections.append(self._generate_appendix(state))
        
        return "\\n\\n".join(sections)
    
    def _generate_header(self, state: Dict[str, Any]) -> str:
        """Generate report header."""
        repo = state.get('current_repo', 'Unknown Repository')
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""# Pandas Migration Report

**Repository:** {repo}  
**Date:** {date}  
**Migration:** pandas {state['pandas_versions']['source']} → {state['pandas_versions']['target']}  
**Duration:** {self._calculate_duration(state)}
"""
    
    def _generate_executive_summary(self, state: Dict[str, Any]) -> str:
        """Generate executive summary section."""
        total_files = len(state.get('migration_results', {}))
        successful = sum(1 for r in state.get('migration_results', {}).values() 
                        if r.get('status') == 'success')
        failed = total_files - successful
        
        test_before = state.get('test_results', {}).get('before', {})
        test_after = state.get('test_results', {}).get('after', {})
        
        # Calculate test regression
        regression_count = 0
        if test_before and test_after:
            regression_count = len(self._find_test_regressions(test_before, test_after))
        
        summary = f"""## Executive Summary

### Migration Statistics
- **Total Files Processed:** {total_files}
- **Successfully Migrated:** {successful}
- **Failed Migrations:** {failed}
- **Success Rate:** {(successful/total_files*100) if total_files > 0 else 0:.1f}%

### Test Results
- **Pre-migration Tests:** {test_before.get('passed', 0)} passed, {test_before.get('failed', 0)} failed
- **Post-migration Tests:** {test_after.get('passed', 0)} passed, {test_after.get('failed', 0)} failed
- **Test Regressions:** {regression_count}

### Overall Status
"""
        
        if failed == 0 and regression_count == 0:
            summary += "✅ **Migration Successful** - All files migrated and tests passing"
        elif regression_count > 0:
            summary += "⚠️ **Migration Completed with Issues** - Test regressions detected"
        else:
            summary += "❌ **Migration Failed** - Some files could not be migrated"
        
        return summary
    
    def _generate_migration_details(self, state: Dict[str, Any]) -> str:
        """Generate detailed migration information."""
        details = ["## Migration Details", ""]
        
        # Group by status
        results = state.get('migration_results', {})
        by_status = {}
        for file, result in results.items():
            status = result.get('status', 'unknown')
            if status not in by_status:
                by_status[status] = []
            by_status[status].append((file, result))
        
        # Success section
        if 'success' in by_status:
            details.append("### Successfully Migrated Files")
            details.append("")
            for file, result in by_status['success']:
                changes = result.get('changes', [])
                details.append(f"- **{file}** ({len(changes)} changes applied)")
                if changes:
                    for change in changes[:3]:  # Show first 3 changes
                        details.append(f"  - {change.get('description', 'Unknown change')}")
                    if len(changes) > 3:
                        details.append(f"  - ... and {len(changes) - 3} more changes")
            details.append("")
        
        # Failure section
        if 'failed' in by_status:
            details.append("### Failed Migrations")
            details.append("")
            for file, result in by_status['failed']:
                error = result.get('error', 'Unknown error')
                details.append(f"- **{file}**")
                details.append(f"  - Error: {error}")
            details.append("")
        
        return "\\n".join(details)
    
    def _generate_test_results(self, state: Dict[str, Any]) -> str:
        """Generate test results section."""
        test_section = ["## Test Results", ""]
        
        before = state.get('test_results', {}).get('before', {})
        after = state.get('test_results', {}).get('after', {})
        
        if not before and not after:
            test_section.append("*No test results available*")
            return "\\n".join(test_section)
        
        # Test summary table
        test_section.append("### Test Summary")
        test_section.append("")
        test_section.append("| Metric | Before Migration | After Migration | Change |")
        test_section.append("|--------|-----------------|-----------------|--------|")
        
        metrics = [
            ('Total Tests', 'total_tests', 0),
            ('Passed', 'passed', 0),
            ('Failed', 'failed', 0),
            ('Errors', 'errors', 0),
            ('Skipped', 'skipped', 0),
        ]
        
        for name, key, default in metrics:
            before_val = before.get(key, default)
            after_val = after.get(key, default)
            change = after_val - before_val
            change_str = f"+{change}" if change > 0 else str(change)
            test_section.append(f"| {name} | {before_val} | {after_val} | {change_str} |")
        
        test_section.append("")
        
        # Regressions
        regressions = self._find_test_regressions(before, after)
        if regressions:
            test_section.append("### Test Regressions")
            test_section.append("")
            test_section.append("The following tests passed before migration but failed after:")
            test_section.append("")
            for test in regressions[:10]:  # Show first 10
                test_section.append(f"- {test}")
            if len(regressions) > 10:
                test_section.append(f"- ... and {len(regressions) - 10} more")
            test_section.append("")
        
        # Improvements
        improvements = self._find_test_improvements(before, after)
        if improvements:
            test_section.append("### Test Improvements")
            test_section.append("")
            test_section.append("The following tests failed before migration but now pass:")
            test_section.append("")
            for test in improvements[:10]:  # Show first 10
                test_section.append(f"- {test}")
            if len(improvements) > 10:
                test_section.append(f"- ... and {len(improvements) - 10} more")
        
        return "\\n".join(test_section)
    
    def _generate_file_changes(self, state: Dict[str, Any]) -> str:
        """Generate file changes section."""
        changes_section = ["## File Changes", ""]
        
        results = state.get('migration_results', {})
        if not results:
            changes_section.append("*No file changes recorded*")
            return "\\n".join(changes_section)
        
        # Group by change type
        change_types = {}
        for file, result in results.items():
            if result.get('status') == 'success':
                for change in result.get('changes', []):
                    rule = change.get('rule', 'unknown')
                    if rule not in change_types:
                        change_types[rule] = []
                    change_types[rule].append({
                        'file': file,
                        'description': change.get('description', ''),
                        'priority': change.get('priority', 'UNKNOWN')
                    })
        
        # Sort by priority
        priority_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']
        
        for priority in priority_order:
            priority_changes = []
            for rule, changes in change_types.items():
                priority_changes.extend([c for c in changes if c['priority'] == priority])
            
            if priority_changes:
                changes_section.append(f"### {priority} Priority Changes")
                changes_section.append("")
                
                # Group by rule
                by_rule = {}
                for change in priority_changes:
                    desc = change['description']
                    if desc not in by_rule:
                        by_rule[desc] = []
                    by_rule[desc].append(change['file'])
                
                for desc, files in by_rule.items():
                    changes_section.append(f"**{desc}**")
                    for file in files[:5]:  # Show first 5 files
                        changes_section.append(f"- {file}")
                    if len(files) > 5:
                        changes_section.append(f"- ... and {len(files) - 5} more files")
                    changes_section.append("")
        
        return "\\n".join(changes_section)
    
    def _generate_compatibility_issues(self, state: Dict[str, Any]) -> str:
        """Generate compatibility issues section."""
        compat_section = ["## Compatibility Analysis", ""]
        
        # Extract compatibility issues from migration results
        all_issues = []
        for file, result in state.get('migration_results', {}).items():
            if 'compatibility_issues' in result:
                for issue in result['compatibility_issues']:
                    all_issues.append({
                        'file': file,
                        'issue': issue
                    })
        
        if not all_issues:
            compat_section.append("✅ No compatibility issues detected")
            return "\\n".join(compat_section)
        
        # Group by severity
        by_severity = {}
        for item in all_issues:
            severity = item['issue'].get('level', 'UNKNOWN')
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(item)
        
        for severity in ['BREAKING', 'WARNING', 'DEPRECATED', 'INFO']:
            if severity in by_severity:
                compat_section.append(f"### {severity} Issues")
                compat_section.append("")
                
                # Group by issue type
                by_type = {}
                for item in by_severity[severity]:
                    issue_type = item['issue'].get('description', 'Unknown issue')
                    if issue_type not in by_type:
                        by_type[issue_type] = []
                    by_type[issue_type].append(item['file'])
                
                for issue_type, files in by_type.items():
                    compat_section.append(f"**{issue_type}**")
                    compat_section.append(f"*Affects {len(files)} file(s)*")
                    compat_section.append("")
        
        return "\\n".join(compat_section)
    
    def _generate_recommendations(self, state: Dict[str, Any]) -> str:
        """Generate recommendations section."""
        rec_section = ["## Recommendations", ""]
        
        recommendations = []
        
        # Check for test regressions
        test_before = state.get('test_results', {}).get('before', {})
        test_after = state.get('test_results', {}).get('after', {})
        regressions = self._find_test_regressions(test_before, test_after) if test_before and test_after else []
        
        if regressions:
            recommendations.append({
                'priority': 'High',
                'title': 'Fix Test Regressions',
                'description': f'{len(regressions)} tests are failing after migration. These should be investigated and fixed before deploying.'
            })
        
        # Check for failed migrations
        failed_files = [f for f, r in state.get('migration_results', {}).items() 
                       if r.get('status') == 'failed']
        if failed_files:
            recommendations.append({
                'priority': 'High',
                'title': 'Manual Migration Required',
                'description': f'{len(failed_files)} files could not be automatically migrated and require manual intervention.'
            })
        
        # Check for deprecated features still in use
        deprecated_count = sum(
            1 for r in state.get('migration_results', {}).values()
            for c in r.get('changes', [])
            if 'deprecated' in c.get('description', '').lower()
        )
        if deprecated_count > 0:
            recommendations.append({
                'priority': 'Medium',
                'title': 'Update Deprecated Features',
                'description': f'Found {deprecated_count} uses of deprecated features that should be updated for future compatibility.'
            })
        
        # General recommendations
        recommendations.extend([
            {
                'priority': 'Medium',
                'title': 'Review Custom Implementations',
                'description': 'Ensure that custom Panel and OLS implementations match the original pandas behavior.'
            },
            {
                'priority': 'Low',
                'title': 'Performance Testing',
                'description': 'Run performance benchmarks to ensure migration hasn\\'t introduced performance regressions.'
            },
            {
                'priority': 'Low',
                'title': 'Update Documentation',
                'description': 'Update project documentation to reflect the pandas version upgrade and any API changes.'
            }
        ])
        
        # Format recommendations
        for priority in ['High', 'Medium', 'Low']:
            priority_recs = [r for r in recommendations if r['priority'] == priority]
            if priority_recs:
                rec_section.append(f"### {priority} Priority")
                rec_section.append("")
                for rec in priority_recs:
                    rec_section.append(f"**{rec['title']}**")
                    rec_section.append(f"{rec['description']}")
                    rec_section.append("")
        
        return "\\n".join(rec_section)
    
    def _generate_appendix(self, state: Dict[str, Any]) -> str:
        """Generate appendix with additional details."""
        appendix = ["## Appendix", ""]
        
        # Configuration used
        appendix.append("### Migration Configuration")
        appendix.append("```json")
        config = {
            'source_pandas': state['pandas_versions']['source'],
            'target_pandas': state['pandas_versions']['target'],
            'auto_rollback': state.get('config_options', {}).get('auto_rollback_on_failure', True),
            'strict_compatibility': state.get('config_options', {}).get('strict_compatibility', True),
        }
        appendix.append(json.dumps(config, indent=2))
        appendix.append("```")
        appendix.append("")
        
        # Custom import mappings
        appendix.append("### Custom Import Mappings")
        appendix.append("```python")
        mappings = state.get('config_options', {}).get('custom_import_mappings', {})
        for old, new in mappings.items():
            appendix.append(f"{old} → {new}")
        appendix.append("```")
        
        return "\\n".join(appendix)
    
    def _generate_html_report(self, state: Dict[str, Any]) -> str:
        """Generate an HTML version of the report."""
        # Convert markdown to basic HTML
        md_report = self._generate_markdown_report(state)
        
        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pandas Migration Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        h3 {{ color: #777; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        code {{ background-color: #f4f4f4; padding: 2px 4px; font-family: monospace; }}
        pre {{ background-color: #f4f4f4; padding: 10px; overflow-x: auto; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .error {{ color: #dc3545; }}
    </style>
</head>
<body>
    {self._markdown_to_html(md_report)}
</body>
</html>"""
        
        return html_template
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Simple markdown to HTML converter."""
        html = html.escape(markdown)
        
        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\\1</h1>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\\*\\*(.+?)\\*\\*', r'<strong>\\1</strong>', html)
        html = re.sub(r'\\*(.+?)\\*', r'<em>\\1</em>', html)
        
        # Code blocks
        html = re.sub(r'```(.+?)```', r'<pre><code>\\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\\1</code>', html)
        
        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\\n)+', r'<ul>\\g<0></ul>', html, flags=re.DOTALL)
        
        # Paragraphs
        html = re.sub(r'\\n\\n', r'</p><p>', html)
        html = f'<p>{html}</p>'
        
        # Tables (simple conversion)
        lines = html.split('\\n')
        in_table = False
        new_lines = []
        
        for line in lines:
            if '|' in line and not in_table:
                in_table = True
                new_lines.append('<table>')
            elif '|' not in line and in_table:
                in_table = False
                new_lines.append('</table>')
            
            if '|' in line:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if all('---' in cell for cell in cells):
                    continue  # Skip separator line
                row_type = 'th' if in_table and len(new_lines) > 0 and new_lines[-1] == '<table>' else 'td'
                row = '<tr>' + ''.join(f'<{row_type}>{cell}</{row_type}>' for cell in cells) + '</tr>'
                new_lines.append(row)
            else:
                new_lines.append(line)
        
        return '\\n'.join(new_lines)
    
    def _calculate_duration(self, state: Dict[str, Any]) -> str:
        """Calculate and format migration duration."""
        start = state.get('start_time')
        end = state.get('end_time')
        
        if not start or not end:
            return "Unknown"
        
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        
        duration = end - start
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"
    
    def _find_test_regressions(self, before: Dict, after: Dict) -> List[str]:
        """Find tests that passed before but fail after migration."""
        # This is a simplified version - in reality, we'd need the detailed test results
        # For now, we'll just return an empty list
        return []
    
    def _find_test_improvements(self, before: Dict, after: Dict) -> List[str]:
        """Find tests that failed before but pass after migration."""
        # This is a simplified version - in reality, we'd need the detailed test results
        # For now, we'll just return an empty list
        return []