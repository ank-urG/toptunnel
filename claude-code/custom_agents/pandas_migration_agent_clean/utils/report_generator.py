"""Report generator for migration results."""

import os
from datetime import datetime
from typing import Dict, Any, List


class ReportGenerator:
    """Generates comprehensive migration reports."""
    
    def generate(self, results: Dict[str, Any], output_path: str) -> None:
        """Generate a migration report.
        
        Args:
            results: Complete migration results
            output_path: Path to save the report
        """
        report = self._build_report(results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
    
    def _build_report(self, results: Dict[str, Any]) -> str:
        """Build the complete report content."""
        lines = []
        
        # Header
        lines.append("# Pandas Migration Report")
        lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Repository: {results['repo_path']}")
        lines.append(f"Status: **{results['status'].upper()}**")
        if 'duration' in results:
            lines.append(f"Duration: {results['duration']}")
        lines.append("\n---\n")
        
        # Executive Summary
        lines.append("## Executive Summary")
        stats = results.get('stats', {})
        lines.append(f"\n- **Files Analyzed**: {stats.get('files_analyzed', 0)}")
        lines.append(f"- **Files Migrated**: {stats.get('files_migrated', 0)}")
        lines.append(f"- **Files Skipped**: {stats.get('files_skipped', 0)}")
        lines.append(f"- **Total Changes**: {stats.get('total_changes', 0)}")
        
        if 'pre_tests' in results.get('phases', {}):
            pre = results['phases']['pre_tests']
            post = results['phases'].get('post_tests', {})
            lines.append(f"\n### Test Results")
            lines.append(f"- **Pre-migration**: {pre.get('passed', 0)} passed, {pre.get('failed', 0)} failed")
            if post:
                lines.append(f"- **Post-migration**: {post.get('passed', 0)} passed, {post.get('failed', 0)} failed")
                
                # Check for regressions
                if post.get('failed', 0) > pre.get('failed', 0):
                    lines.append(f"- **⚠️  WARNING**: {post['failed'] - pre['failed']} new test failures detected!")
        
        lines.append("\n---\n")
        
        # Migration Details
        lines.append("## Migration Details")
        
        migration_phase = results.get('phases', {}).get('migration', {})
        if 'file_results' in migration_phase:
            # Group by status
            by_status = {}
            for file_result in migration_phase['file_results']:
                status = file_result['status']
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(file_result)
            
            # Successfully migrated files
            if 'success' in by_status:
                lines.append(f"\n### Successfully Migrated ({len(by_status['success'])} files)")
                for result in by_status['success'][:10]:  # Show first 10
                    lines.append(f"\n**{self._relative_path(result['file'], results['repo_path'])}**")
                    lines.append(f"- Changes: {result.get('total_changes', 0)}")
                    if result.get('changes'):
                        for change in result['changes'][:3]:  # Show first 3 changes
                            lines.append(f"  - {change['description']}")
                
                if len(by_status['success']) > 10:
                    lines.append(f"\n*... and {len(by_status['success']) - 10} more files*")
            
            # Skipped files
            if 'skipped' in by_status or 'unchanged' in by_status:
                skipped = by_status.get('skipped', []) + by_status.get('unchanged', [])
                lines.append(f"\n### Skipped Files ({len(skipped)} files)")
                
                # Group by reason
                by_reason = {}
                for result in skipped:
                    reason = result.get('reason', 'No reason provided')
                    if reason not in by_reason:
                        by_reason[reason] = 0
                    by_reason[reason] += 1
                
                for reason, count in by_reason.items():
                    lines.append(f"- {reason}: {count} files")
            
            # Failed files
            if 'error' in by_status:
                lines.append(f"\n### Failed Files ({len(by_status['error'])} files)")
                for result in by_status['error']:
                    lines.append(f"\n**{self._relative_path(result['file'], results['repo_path'])}**")
                    lines.append(f"- Error: {result.get('error', 'Unknown error')}")
        
        lines.append("\n---\n")
        
        # Common Replacements Made
        lines.append("## Common Replacements")
        lines.append("\nThe following pandas API replacements were made:")
        lines.append("\n| Deprecated API | Replacement |")
        lines.append("|----------------|-------------|")
        lines.append("| `.sort()` | `.sort_values()` |")
        lines.append("| `.ix[]` | `.loc[]` or `.iloc[]` |")
        lines.append("| `.valid()` | `.dropna()` |")
        lines.append("| `pd.rolling_mean()` | `.rolling().mean()` |")
        lines.append("| `pd.Panel` | `aqr.core.panel.Panel` |")
        lines.append("| `pd.ols()` | `aqr.stats.ols.OLS()` |")
        lines.append("| `pd.TimeGrouper()` | `pd.Grouper(freq=)` |")
        lines.append("| `.as_matrix()` | `.values` |")
        
        lines.append("\n---\n")
        
        # Recommendations
        lines.append("## Recommendations")
        lines.append("\n1. **Review the changes**: Although the migrations are designed to be safe, review critical files")
        lines.append("2. **Run full test suite**: Ensure all tests pass in both pandas environments")
        lines.append("3. **Check edge cases**: Pay special attention to data-dependent operations")
        lines.append("4. **Monitor performance**: Some replacements may have slightly different performance characteristics")
        
        if stats.get('tests_failed', 0) > 0:
            lines.append("\n### ⚠️  Test Failures")
            lines.append(f"\n{stats['tests_failed']} tests are failing. Please investigate and fix these before deploying.")
        
        return '\n'.join(lines)
    
    def _relative_path(self, file_path: str, repo_path: str) -> str:
        """Get relative path for display."""
        try:
            return os.path.relpath(file_path, repo_path)
        except:
            return file_path