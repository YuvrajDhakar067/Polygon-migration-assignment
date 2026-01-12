# Cloud Storage Implementation

Added support for multiple cloud storage providers so test cases can be stored in different places. You can now use AWS S3, Azure Blob Storage, Cloudflare R2, Google Drive, or just local file system.

## What's Included

Built a storage manager system that lets you swap between different providers easily. All of them work the same way - you just change an environment variable and it switches.

**Supported providers:**
- AWS S3 - works with any S3 bucket
- Azure Blob Storage - uses service principal auth
- Cloudflare R2 - S3-compatible, so it was pretty easy to add
- Google Drive - uses service accounts, had to work around the quota limitation
- Local Storage - just saves files to disk, good for testing

## How It Works

Created a base `StorageManager` class that all providers inherit from. Each provider implements the same three methods:
- `upload_test_case()` - uploads input and output files
- `empty_blob()` - deletes all files for a problem
- `upload_file()` - uploads any file

There's a factory function `get_storage_manager()` that returns the right one based on your `STORAGE_TYPE` setting.

## Setup

Just set this in your `.env`:
```
STORAGE_TYPE=s3
```

Or use `azure`, `r2`, `gdrive`, or `local`. Then add the credentials for whatever provider you picked.

For AWS you need access key and secret. For Azure you need the account URL, tenant ID, client ID, username, and password. R2 is similar to S3. Google Drive needs a service account JSON file and a folder ID (shared with the service account). Local just needs a path.

## File Structure

Test cases get saved like this:
```
test_cases/{problem_id}/01      # input
test_cases/{problem_id}/01.a    # output
```

Pretty straightforward. Each problem gets its own folder.

## Why This Is Useful

You can switch providers without changing any code - just update the env variable. All providers work the same way so there's no learning curve. If you want to add a new provider later, just implement those three methods.

Also gives you options - S3 and Azure cost money but R2 and Google Drive have free tiers. Local storage is free and works great for development.

## Testing

Tested with all providers. Files upload correctly, old files get deleted before new ones, and errors are handled properly. Google Drive was a bit tricky because service accounts can't own files directly, so you have to share a folder with them first.

## Notes

Default is `local` so you don't need any cloud accounts to get started. The migration flow stays the same - cloud storage is optional and happens separately from the database migration.
