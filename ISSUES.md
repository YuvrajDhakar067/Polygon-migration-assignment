# Issues Analysis

## Summary

| Type | Critical | High | Medium | Low | Total |
|------|----------|------|--------|-----|-------|
| Product Issues | 0 | 2 | 3 | 1 | 6 |
| Code Issues | 0 | 2 | 3 | 2 | 7 |

---

## Product Issues

> Product issues are user-facing problems: broken functionality, missing validation, poor UX, data integrity risks visible to users.

### [P1] Old Test Cases Don't Get Deleted When Re-migrating

**Severity**: High

**Location**: `problems/views.py:520-553`

**Description**:
When you re-migrate a problem that used to have more test cases, the old extra ones just stay in the database. The code updates existing test cases and creates new ones, but never deletes the ones that are no longer in Polygon.

**Impact**:
- Database has stale test cases that dont exist in Polygon anymore
- Test case count in DB doesnt match actual Polygon count
- Users see wrong test cases when viewing problem
- Database and cloud storage get out of sync (storage correctly deletes old files, but DB doesnt)

**Suggested Fix**:
Delete all existing test cases before creating new ones, similar to how cloud storage does it:
```python
ProblemTestCase.objects.filter(problem=problem_obj).delete()
# Then create all new ones
```

---

### [P2] Duplicate Slug Error When Same Title

**Severity**: High

**Location**: `problems/views.py:288, 349, 373`

**Description**:
If two different Polygon problems have the same title (like "Two Sum"), the slug will be the same. When trying to create the second problem, Django throws a unique constraint error because slug field is unique.

**Impact**:
- Migration fails with database error
- User sees confusing IntegrityError page
- Second problem cant be migrated at all
- No way to work around it

**Suggested Fix**:
Make slug unique by checking if it exists and appending a number:
```python
base_slug = slugify(title)
slug = base_slug
counter = 1
while Problem.objects.filter(slug=slug).exclude(pk=problem_obj.pk if problem_obj else None).exists():
    slug = f"{base_slug}-{counter}"
    counter += 1
```

---

### [P3] Test Case Data Truncation Inconsistency

**Severity**: Medium

**Location**: `problems/views.py:530-531`

**Description**:
Test cases saved to database are truncated to 260 characters, but full data is saved to cloud storage. This creates inconsistency - DB has partial data, storage has full data.

**Impact**:
- Users cant see full test case in database
- If storage fails, you lose full test data
- Hard to debug issues with truncated data
- Documentation might say 1000 chars but code does 260

**Suggested Fix**:
Either increase DB limit to match storage, or document the limitation clearly. Better to increase to at least 1000 chars since TextField can handle it.

---

### [P4] No Confirmation for Destructive Actions

**Severity**: Medium

**Location**: `problems/templates/problems/index.html` (migrate buttons)

**Description**:
Clicking "Migrate to Cloud Storage" or "Migrate Test Cases to DB" immediately overwrites existing data without asking user for confirmation.

**Impact**:
- Accidental clicks can overwrite good data
- No way to cancel once clicked
- User might lose data by mistake

**Suggested Fix**:
Add JavaScript confirmation dialog before form submission:
```javascript
if (!confirm('This will overwrite existing test cases. Continue?')) {
    return false;
}
```

---

### [P5] Missing Message When No Sample Tests

**Severity**: Medium

**Location**: `problems/views.py:443-467`

**Description**:
If a problem has 0 sample test cases, the code just creates an empty list and continues. No warning or info message to user about this.

**Impact**:
- User might not realize there are no sample tests
- Could be confusing why sample section is empty
- No feedback about what happened

**Suggested Fix**:
Add info message when sample_tests list is empty:
```python
if not sample_tests:
    context['info'] = "No sample test cases found in Polygon."
```

---

### [P6] No Progress Indicator for Long Operations

**Severity**: Low

**Location**: All migration operations

**Description**:
When fetching/migrating problems with many test cases, it can take 30+ seconds. User sees no progress, might think page is frozen.

**Impact**:
- Users might refresh page thinking its broken
- Poor user experience
- No feedback during long waits

**Suggested Fix**:
Add loading spinner or progress bar during migration operations. Even a simple "Please wait..." message would help.

---

## Code Issues

> Code issues are technical problems: bugs, security vulnerabilities, performance problems, code quality concerns, architectural issues.

### [C1] Test Cases Not Deleted on Re-migration

**Severity**: High

**Location**: `problems/views.py:520-553`

**Description**:
The code updates existing test cases by index, but if new count is less than old count, extra test cases remain in database. Only updates/creates, never deletes.

**Code**:
```python
existing_test_cases = list(ProblemTestCase.objects.filter(problem=problem_obj).order_by('order'))
for idx, test in enumerate(test_cases):
    if idx < len(existing_test_cases):
        # Update existing
    else:
        # Create new
# Missing: Delete extra ones if len(test_cases) < len(existing_test_cases)
```

**Impact**:
- Database inconsistency
- Memory waste storing unused data
- Wrong test case count
- DB and storage out of sync

**Suggested Fix**:
Delete all before creating:
```python
ProblemTestCase.objects.filter(problem=problem_obj).delete()
# Then create all fresh
```

---

### [C2] Slug Collision Not Handled

**Severity**: High

**Location**: `problems/views.py:288, 349, 373`

**Description**:
Slug is generated from title using `slugify(title)`. If two problems have same title, second one will fail with IntegrityError on unique constraint.

**Impact**:
- Migration crashes with database error
- No graceful handling
- User sees ugly error page

**Suggested Fix**:
Check for existing slug and append number:
```python
base_slug = slugify(title)
slug = base_slug
counter = 1
while Problem.objects.filter(slug=slug).exclude(pk=problem_obj.pk if problem_obj else None).exists():
    slug = f"{base_slug}-{counter}"
    counter += 1
```

---

### [C3] Truncation Limit Mismatch

**Severity**: Medium

**Location**: `problems/views.py:530`

**Description**:
Code truncates to 260 chars but comments/documentation suggest 1000. Actual limit is 260.

**Code**:
```python
truncated_input = input_data[:260]  # Says 260
truncated_output = output_data[:260]
```

**Impact**:
- Confusing for developers
- Less data stored than expected
- Inconsistent with documentation

**Suggested Fix**:
Either change to 1000 or update all docs to say 260. Better to use 1000 since TextField supports it.

---

### [C4] No Transaction for Test Case Migration

**Severity**: Medium

**Location**: `problems/views.py:500-555`

**Description**:
Test case migration is not wrapped in transaction. If it fails halfway, some test cases are saved, some arent. Partial state.

**Impact**:
- Database in inconsistent state on failure
- Hard to recover
- Some test cases saved, some missing

**Suggested Fix**:
Wrap in transaction.atomic():
```python
with transaction.atomic():
    # Delete old
    # Create new
```

---

### [C5] Redis Cache Key Pattern Inconsistency

**Severity**: Medium

**Location**: `problems/polygon_api.py:787, 829, 889, 952`

**Description**:
Different methods use different key patterns. Some use `polygon_test_cases:{polygon_id}`, some use different patterns. Hard to track and clear cache.

**Impact**:
- Cache might not be cleared properly
- Memory leaks if keys not deleted
- Confusing to debug cache issues

**Suggested Fix**:
Standardize on one pattern everywhere:
```python
CACHE_KEY_PATTERN = f"polygon_test_cases:{polygon_id}"
```

---

### [C6] Exception Swallowed in Solution Fetching

**Severity**: Low

**Location**: `problems/views.py:496-498`

**Description**:
Exception when fetching solution is caught and logged, but main_solution is just set to None. No user feedback.

**Code**:
```python
except Exception as e:
    logger.error('Error fetching solution: %s', e)
    main_solution = None  # Silent failure
```

**Impact**:
- User doesnt know solution fetch failed
- Silent failures are hard to debug
- Missing data without explanation

**Suggested Fix**:
Add warning message to context or at least log more details.

---

### [C7] Hardcoded Sample Test Count Logic

**Severity**: Low

**Location**: `problems/polygon_api.py:376`

**Description**:
Sample test detection relies on Polygon's `useInStatements` flag, but code also assumes first 3 are samples in some places. Inconsistent logic.

**Impact**:
- Might mark wrong tests as samples
- Logic scattered in multiple places
- Hard to maintain

**Suggested Fix**:
Use only Polygon's `useInStatements` flag consistently everywhere.

---

## Edge Case Analysis

### Question 1: Empty Sample Test Cases

> A Polygon problem has **0 sample test cases** but **15 regular test cases**. What happens when you migrate this problem?

**Your Analysis**:

Looking at the code in `views.py:443-467`, here's what happens:

1. **What code path executes?**
   - When migrating test cases to DB, it filters for sample tests:
   ```python
   sample_tests = [test for test in test_cases if test.get('is_sample', False)]
   ```
   - If there are 0 samples, this list is empty
   - The loop `for idx, test in enumerate(sample_tests):` never runs

2. **What database state results?**
   - `SampleTestCase` table: If problem was migrated before with samples, old samples remain. If first time, table stays empty.
   - `ProblemTestCase` table: All 15 regular tests are saved with `is_sample=False`

3. **What happens on re-migration if samples previously existed?**
   - Old sample cases from previous migration are NOT deleted
   - They stay in database even though Polygon has 0 samples now
   - This is a bug - old samples should be cleaned up

4. **Is the behavior correct?**
   - Partially. It correctly saves 0 samples, but doesnt clean up old samples if they existed before. Should delete all sample cases first.

**Code References**:
- `views.py:443` - Filtering sample tests
- `views.py:445` - Getting existing sample cases
- `views.py:447-467` - Loop that never runs if empty

---

### Question 2: Test Case Count Reduction

> A problem is migrated with **20 test cases**. Later, the problem setter removes 8 test cases on Polygon (now 12 remain). The problem is re-migrated. What happens?

**Your Analysis**:

This is a serious bug. Here's what happens:

1. **Database state before and after:**
   - Before: 20 `ProblemTestCase` records
   - During: Gets 12 test cases from Polygon. Updates first 12 existing records (idx 0-11). Creates 0 new ones. Last 8 test cases (idx 12-19) are NEVER deleted.
   - After: Database has 20 records (12 updated, 8 stale)

2. **Cloud storage state before and after:**
   - Before: 20 test files (01-20, 01.a-20.a)
   - During: Calls `storage_manager.empty_blob()` - DELETES all old files. Uploads 12 new test cases.
   - After: Storage has correct 12 files

3. **Consistency between DB and storage:**
   - Database: 20 records (wrong)
   - Cloud storage: 12 files (correct)
   - They are OUT OF SYNC

4. **Data integrity issues:**
   - Database shows wrong test case count
   - Old test data still in DB
   - Users see stale test cases
   - DB and storage dont match

**Code References**:
- `views.py:520` - Gets existing test cases
- `views.py:534` - Only updates if `idx < len(existing_test_cases)`, never deletes extras
- `polygon_api.py:737` - Storage correctly deletes all first
- `storage_manager.py:75` - `empty_blob()` deletes all files

---

### Question 3: Duplicate Problem Titles

> Two different Polygon problems have the exact same title: "Two Sum". You migrate the first one successfully. Then you try to migrate the second one. What happens?

**Your Analysis**:

This will crash with a database error. Here's why:

1. **Which field causes the issue?**
   - The `slug` field. It's generated from title and has `unique=True` constraint.

2. **When does the error occur?**
   - First migration: Title "Two Sum" → slug "two-sum" → creates successfully
   - Second migration: Title "Two Sum" → slug "two-sum" (same!) → tries to create → IntegrityError

3. **What does the user see?**
   - Error page with `IntegrityError: duplicate key value violates unique constraint "problems_problem_slug_key"`
   - Confusing database error message
   - Second problem cant be migrated

4. **Is first problem affected?**
   - No, first problem stays in database unchanged
   - But second one cant be added

**Code References**:
- `views.py:288` - Slug generation: `slug = slugify(title)`
- `models.py:58` - Slug field: `slug = models.SlugField(unique=True)`
- `views.py:372` - Creates problem without checking slug uniqueness

---

### Question 4: Data Truncation

> When test cases are saved to the database via "Migrate Test Cases to DB", some data is intentionally discarded. What data is lost? Why might this cause problems?

**Your Analysis**:

1. **Where truncation happens:**
   ```python
   # views.py:530-531
   truncated_input = input_data[:260]
   truncated_output = output_data[:260]
   ```

2. **What the limit is:**
   - 260 characters for both input and output
   - Anything beyond that is discarded

3. **What types of problems are affected:**
   - Graph problems (large adjacency lists)
   - Array problems with many elements
   - String problems with long inputs
   - Any test case with input/output > 260 chars

4. **DB vs cloud storage consistency:**
   - Database has: First 260 chars only
   - Cloud storage has: Full data (no truncation)
   - They dont match - inconsistency

5. **Why this causes problems:**
   - Incomplete test data in DB - cant reconstruct full test from DB alone
   - If storage fails, you lose full test data
   - Large test cases break - first 260 chars might just be header, actual data is lost
   - Hard to debug - when checking DB you only see partial test
   - Documentation mismatch - code says 260 but docs might say 1000

**Code References**:
- `views.py:530-531` - Truncation happens here
- `models.py:134-135` - `input` and `output` are `TextField()` which can hold much more
- `polygon_api.py:744` - Storage saves full data without truncation

---

## Severity Guidelines

Use these definitions when assigning severity:

| Severity | Definition | Examples |
|----------|------------|----------|
| **Critical** | System broken, security vulnerability, data loss | SQL injection, authentication bypass, data corruption |
| **High** | Major functionality broken, significant data integrity risk | Feature doesn't work, orphaned records, race conditions |
| **Medium** | Feature partially broken, poor UX, code maintainability | Missing validation, confusing errors, code duplication |
| **Low** | Minor issues, cosmetic, best practice violations | Unused imports, inconsistent formatting, missing logs |

---

## Notes

The test case deletion bug (C1/P1) is the most critical one - it causes real data inconsistency between DB and storage.

The slug collision (C2/P2) will definitely happen in real world since common problem names get reused a lot.

The truncation at 260 chars seems way too small. Should be at least 1000 since TextField supports it.

Cloud storage migration correctly deletes old files first, but DB migration doesnt. This inconsistency in design is confusing.

No rollback mechanism if migration fails partway through. If it crashes, database might be in partial state.

Redis caching works but the key patterns are inconsistent across different methods. Should standardize.
