# Polygon Migration Tool - How it Works

## User Flows

### 1. Login

So basically when you open the app, it kicks you to the login page first. You cant do anything without logging in.

How it works:
- Go to localhost:8000
- It redirects you to /users/login/
- Enter your username password
- Hit login button
- If correct - you go to main page
- If wrong - shows error, try again

The backend just checks your username/password against the database. If it matches, it sets a session cookie so you stay logged in.

---

### 2. Fetching Problem from Polygon

This is the main thing. You put the polygon problem id in the input box and click fetch.

What you send:
- Just the problem_id (like 501572)

What happens behind the scenes:

First it checks if this problem already exists in our database. If yes, it loads that data.

Then it starts calling Polygon APIs one by one:

1. Calls problem.updateWorkingCopy - this is like refreshing to get latest version
2. Calls problem.solutions - gets list of solution files
3. Calls problem.info - gets time limit, memory limit etc
4. Downloads the problem package (its a zip file) - extracts the html file from it
5. Parses the html to get title, description, input format, output format
6. Gets all test cases - first gets the list, then for each test downloads input and output separately
7. Stores test cases in redis (so we dont have to fetch again)
8. Checks what checker is being used

What you see:
- Problem title and description shows up
- Test case count appears
- Some buttons appear to migrate stuff

---

### 3. Migrate to Database

After fetching, you can save it to database. Click the "Create/Update in Database" button.

You can also select difficulty (easy/medium/hard) and add some tags before saving.

What happens:
- If problem with this polygon_id exists - it updates it
- If not - creates new record
- Saves all the problem info - title, description, limits etc
- If you selected tags, it links them to the problem
- Also fetches the main solution code and saves it

Tables that get updated:
- problems_problem - the main problem record
- problems_tag - creates tags if they dont exist
- problems_problem_tags - links problem to tags

---

### 4. Migrate Test Cases to Database

Theres a separate button for this. It saves the test cases to database.

What happens:
- Gets test cases from redis (or fetches from polygon if not in cache)
- Deletes any old test cases for this problem
- Creates new records for each test case
- Only saves first 260 characters of input/output (to save space)
- Marks first 3 as sample test cases

---

### 5. Migrate to Cloud Storage

This one uploads the actual test case files to storage. Right now we're using local storage but it can also work with S3, Azure, Google Drive etc.

What happens:
- First checks if problem exists in DB (you need to do step 3 first)
- Gets test cases from redis/polygon
- Deletes old files if any
- Uploads each test case:
  - Input goes to 01, 02, 03 etc
  - Output goes to 01.a, 02.a, 03.a etc
- If theres a custom checker, uploads that too as custom_checker.cpp
- Clears redis cache after done

Where files go (local storage):
storage/polygon-storage/test_cases/1/
  01      <- test 1 input
  01.a    <- test 1 output
  02
  02.a
  ...

---

## Data Models

### problems_problem

This is the main table. Stores everything about a problem.

Key columns:
- id - auto id
- polygon_id - the polygon problem id, unique
- title - problem name
- description - problem statement html
- input_format - input description
- output_format - output description
- notes - any notes
- time_limit - in milliseconds, default 2000
- memory_limit - in MB, default 256
- difficulty - easy/medium/hard, can be empty
- main_correct_solution - the solution code
- checker_type - like wcmp.cpp or checker.cpp
- created_at - when created
- updated_at - when last updated

### problems_tag

Just stores tag names.

Columns:
- id
- name (unique)

Examples: math, dp, greedy, graphs

### problems_problem_tags

Links problems to tags. Many to many relationship.

Columns:
- id
- problem_id - foreign key to problem
- tag_id - foreign key to tag

### problems_testcase

Stores test cases.

Columns:
- id
- problem_id - fk to problem
- input_data - truncated to 260 chars
- output_data - truncated
- is_sample - true for first 3 tests
- description - optional
- order - 1, 2, 3...

### users_customuser

User accounts.

Columns:
- id
- username
- password (hashed)
- email
- is_staff
- is_active

---

## External Stuff

### Polygon API

Base url: https://polygon.codeforces.com/api/

Authentication:

You need API key and secret from your polygon account. Every request needs to be signed.

The signing is kinda complicated:
- Sort all parameters
- Make a string with method name + params + secret
- Hash it with SHA512
- Add the hash to request

APIs we use:

problem.info - get time/memory limits
problem.updateWorkingCopy - refresh problem
problem.solutions - list of solutions
problem.solution - get solution code
problem.tests - list test cases
problem.testInput - get test input
problem.testAnswer - get test output
problem.checker - get checker name
problem.package - download zip with html

### Storage

We support multiple storage backends:
- Local (just saves to disk)
- AWS S3
- Azure Blob
- Google Drive
- Cloudflare R2

Current setup uses local storage. Files go to:
storage/polygon-storage/test_cases/{problem_id}/

File naming:
- Inputs: 01, 02, 03... (two digits)
- Outputs: 01.a, 02.a, 03.a...

### Redis

Used for caching test cases. So when you fetch a problem, the test cases get stored in redis. Next time you need them (like for migration), it reads from redis instead of calling polygon api again.

Key format: polygon_test_cases:501572

Gets deleted after cloud storage migration is done.
