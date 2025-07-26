# User Prompt Template

## Task: Migrate Repository from pandas {source_version} to {target_version}

Repository Path: `{repo_path}`

### Requirements:
1. Identify all Python files that use pandas
2. Detect deprecated features that need migration
3. Apply migration rules while maintaining backward compatibility
4. Run tests before and after migration
5. Generate a detailed report

### Custom Import Mappings:
{import_mappings}

### Configuration:
- Auto rollback on failure: {auto_rollback}
- Create backups: {create_backups}
- Test timeout: {test_timeout} seconds
- Strict compatibility: {strict_compatibility}

### Expected Deliverables:
1. Migrated code files with all deprecated features updated
2. Test results comparison (before vs after)
3. Comprehensive migration report
4. List of any remaining compatibility issues

Please proceed with the migration following the established workflow.