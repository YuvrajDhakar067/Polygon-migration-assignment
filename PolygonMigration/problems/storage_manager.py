# storage manager for different cloud providers
import logging
import os
import shutil
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StorageManager(ABC):
    # base class for storage - need to implement these methods
    
    @abstractmethod
    def upload_test_case(self, container_name, db_problem_id, test_number, input_data, output_data):
        # upload test case input and output files
        pass
    
    @abstractmethod
    def empty_blob(self, container_name, problem_id):
        # delete all files for a problem
        pass
    
    @abstractmethod
    def upload_file(self, container_name, file_path, file_data):
        # upload any file
        pass


class S3StorageManager(StorageManager):
    # S3 implementation
    
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name='us-east-1'):
        try:
            import boto3
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
            logger.info("S3 client initialized")
        except ImportError:
            logger.error("need to install boto3: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"error setting up S3: {e}")
            raise
    
    def upload_test_case(self, container_name, db_problem_id, test_number, input_data, output_data):
        # upload test case files to S3
        input_key = f"test_cases/{db_problem_id}/{test_number:02d}"
        output_key = f"test_cases/{db_problem_id}/{test_number:02d}.a"
        
        try:
            # upload input file
            self.s3_client.put_object(
                Bucket=container_name,
                Key=input_key,
                Body=input_data.encode('utf-8')
            )
            logger.info(f"uploaded input test #{test_number}")
            
            # upload output file
            self.s3_client.put_object(
                Bucket=container_name,
                Key=output_key,
                Body=output_data.encode('utf-8')
            )
            logger.info(f"uploaded output test #{test_number}")
        except Exception as e:
            logger.error(f"failed to upload test case {test_number}: {e}")
            raise
    
    def empty_blob(self, container_name, problem_id):
        # delete all test cases for a problem
        prefix = f"test_cases/{problem_id}/"
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=container_name, Prefix=prefix)
            
            deleted_count = 0
            for page in pages:
                if 'Contents' in page:
                    objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects_to_delete:
                        self.s3_client.delete_objects(
                            Bucket=container_name,
                            Delete={'Objects': objects_to_delete}
                        )
                        deleted_count += len(objects_to_delete)
            
            logger.info(f"deleted {deleted_count} files for problem {problem_id}")
        except Exception as e:
            logger.error(f"error deleting files: {e}")
            raise
    
    def upload_file(self, container_name, file_path, file_data):
        # upload any file to S3
        try:
            self.s3_client.put_object(
                Bucket=container_name,
                Key=file_path,
                Body=file_data
            )
            logger.info(f"uploaded file {file_path}")
        except Exception as e:
            logger.error(f"upload failed: {e}")
            raise


# Cloudflare R2 Storage - FREE tier (10GB storage, no egress fees)
class R2StorageManager(StorageManager):
    
    def __init__(self, account_id, access_key_id, secret_access_key):
        try:
            import boto3
            # R2 uses S3-compatible API
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name='auto'  # R2 doesn't use regions
            )
            logger.info(f"R2 client initialized for account: {account_id}")
        except ImportError:
            logger.error("need to install boto3: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"error setting up R2: {e}")
            raise
    
    def upload_test_case(self, container_name, db_problem_id, test_number, input_data, output_data):
        input_key = f"test_cases/{db_problem_id}/{test_number:02d}"
        output_key = f"test_cases/{db_problem_id}/{test_number:02d}.a"
        
        try:
            self.s3_client.put_object(
                Bucket=container_name,
                Key=input_key,
                Body=input_data.encode('utf-8')
            )
            logger.info(f"R2: uploaded input test #{test_number}")
            
            self.s3_client.put_object(
                Bucket=container_name,
                Key=output_key,
                Body=output_data.encode('utf-8')
            )
            logger.info(f"R2: uploaded output test #{test_number}")
        except Exception as e:
            logger.error(f"R2: failed to upload test case {test_number}: {e}")
            raise
    
    def empty_blob(self, container_name, problem_id):
        prefix = f"test_cases/{problem_id}/"
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=container_name, Prefix=prefix)
            
            deleted_count = 0
            for page in pages:
                if 'Contents' in page:
                    objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects_to_delete:
                        self.s3_client.delete_objects(
                            Bucket=container_name,
                            Delete={'Objects': objects_to_delete}
                        )
                        deleted_count += len(objects_to_delete)
            
            logger.info(f"R2: deleted {deleted_count} files for problem {problem_id}")
        except Exception as e:
            logger.error(f"R2: error deleting files: {e}")
            raise
    
    def upload_file(self, container_name, file_path, file_data):
        try:
            self.s3_client.put_object(
                Bucket=container_name,
                Key=file_path,
                Body=file_data
            )
            logger.info(f"R2: uploaded file {file_path}")
        except Exception as e:
            logger.error(f"R2: upload failed: {e}")
            raise


# Google Drive Storage - FREE 15GB
class GoogleDriveStorageManager(StorageManager):
    
    def __init__(self, credentials_json_path, folder_id=None):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaInMemoryUpload
            
            self.MediaInMemoryUpload = MediaInMemoryUpload
            
            import os
            if not os.path.exists(credentials_json_path):
                raise FileNotFoundError(f"Credentials file not found: {credentials_json_path}")
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_json_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.service = build('drive', 'v3', credentials=credentials)
            self.root_folder_id = folder_id
            logger.info("Google Drive client initialized")
        except ImportError:
            logger.error("Install: pip install google-api-python-client google-auth")
            raise
        except Exception as e:
            logger.error(f"Google Drive setup error: {e}")
            raise
    
    def _get_or_create_folder(self, folder_name, parent_id=None):
        # Use root_folder_id as parent if no parent specified
        effective_parent = parent_id or self.root_folder_id
        
        # Find existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if effective_parent:
            query += f" and '{effective_parent}' in parents"
        
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        
        # Create folder - must have parent for service accounts
        if not effective_parent:
            raise Exception("Google Drive: root_folder_id required for service accounts")
        
        metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [effective_parent]
        }
        
        folder = self.service.files().create(body=metadata, fields='id').execute()
        return folder['id']
    
    def upload_test_case(self, container_name, db_problem_id, test_number, input_data, output_data):
        try:
            # Create folder structure: container/test_cases/problem_id/
            container_folder = self._get_or_create_folder(container_name)
            test_cases_folder = self._get_or_create_folder('test_cases', container_folder)
            problem_folder = self._get_or_create_folder(str(db_problem_id), test_cases_folder)
            
            # Upload input file
            input_filename = f"{test_number:02d}"
            input_media = self.MediaInMemoryUpload(input_data.encode('utf-8'), mimetype='text/plain')
            self.service.files().create(
                body={'name': input_filename, 'parents': [problem_folder]},
                media_body=input_media
            ).execute()
            logger.info(f"Google Drive: uploaded input test #{test_number}")
            
            # Upload output file
            output_filename = f"{test_number:02d}.a"
            output_media = self.MediaInMemoryUpload(output_data.encode('utf-8'), mimetype='text/plain')
            self.service.files().create(
                body={'name': output_filename, 'parents': [problem_folder]},
                media_body=output_media
            ).execute()
            logger.info(f"Google Drive: uploaded output test #{test_number}")
            
        except Exception as e:
            logger.error(f"Google Drive: upload failed for test {test_number}: {e}")
            raise
    
    def empty_blob(self, container_name, problem_id):
        try:
            # Find and delete all files in problem folder
            container_folder = self._get_or_create_folder(container_name)
            test_cases_folder = self._get_or_create_folder('test_cases', container_folder)
            
            query = f"name='{problem_id}' and '{test_cases_folder}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id)").execute()
            
            deleted_count = 0
            for file in results.get('files', []):
                self.service.files().delete(fileId=file['id']).execute()
                deleted_count += 1
            
            logger.info(f"Google Drive: deleted {deleted_count} items for problem {problem_id}")
        except Exception as e:
            logger.error(f"Google Drive: delete failed: {e}")
            raise
    
    def upload_file(self, container_name, file_path, file_data):
        try:
            container_folder = self._get_or_create_folder(container_name)
            
            # Create parent folders if needed
            parts = file_path.split('/')
            parent_id = container_folder
            for folder_name in parts[:-1]:
                parent_id = self._get_or_create_folder(folder_name, parent_id)
            
            # Upload file
            filename = parts[-1]
            if isinstance(file_data, str):
                file_data = file_data.encode('utf-8')
            media = self.MediaInMemoryUpload(file_data, mimetype='application/octet-stream')
            self.service.files().create(
                body={'name': filename, 'parents': [parent_id]},
                media_body=media
            ).execute()
            logger.info(f"Google Drive: uploaded {file_path}")
        except Exception as e:
            logger.error(f"Google Drive: file upload error: {e}")
            raise


# Local file storage - FREE, no account needed
class LocalStorageManager(StorageManager):
    
    def __init__(self, base_path):
        self.base_path = base_path
        # Create base directory if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        logger.info(f"Local storage initialized at: {base_path}")
    
    def upload_test_case(self, container_name, db_problem_id, test_number, input_data, output_data):
        # Create directory structure: base_path/container/test_cases/problem_id/
        problem_dir = os.path.join(self.base_path, container_name, 'test_cases', str(db_problem_id))
        os.makedirs(problem_dir, exist_ok=True)
        
        # Input file: test_cases/{problem_id}/{test_number}
        input_file = os.path.join(problem_dir, f"{test_number:02d}")
        # Output file: test_cases/{problem_id}/{test_number}.a
        output_file = os.path.join(problem_dir, f"{test_number:02d}.a")
        
        try:
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write(input_data)
            logger.info(f"saved input test #{test_number} to {input_file}")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_data)
            logger.info(f"saved output test #{test_number} to {output_file}")
        except Exception as e:
            logger.error(f"failed to save test case {test_number}: {e}")
            raise
    
    def empty_blob(self, container_name, problem_id):
        # Delete all test cases for a problem
        problem_dir = os.path.join(self.base_path, container_name, 'test_cases', str(problem_id))
        try:
            if os.path.exists(problem_dir):
                shutil.rmtree(problem_dir)
                logger.info(f"deleted test cases directory: {problem_dir}")
            else:
                logger.info(f"no files to delete for problem {problem_id}")
        except Exception as e:
            logger.error(f"error deleting files: {e}")
            raise
    
    def upload_file(self, container_name, file_path, file_data):
        # Upload any file
        full_path = os.path.join(self.base_path, container_name, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            mode = 'wb' if isinstance(file_data, bytes) else 'w'
            with open(full_path, mode) as f:
                f.write(file_data)
            logger.info(f"saved file to {full_path}")
        except Exception as e:
            logger.error(f"file save failed: {e}")
            raise


# Azure implementation (keeping for compatibility)
class AzureBlobManager(StorageManager):
    
    def __init__(self, account_url, tenant_id, client_id, username, password):
        from azure.identity import UsernamePasswordCredential
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import ClientAuthenticationError
        
        self.account_url = account_url
        self.blob_service_client = None
        
        logger.info("connecting to Azure...")
        try:
            credential = UsernamePasswordCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                username=username,
                password=password
            )
            self.blob_service_client = BlobServiceClient(
                account_url=self.account_url, 
                credential=credential
            )
            logger.info("Azure connected")
        except ClientAuthenticationError as e:
            logger.warning(f"Azure auth failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Azure setup error: {e}")
            raise
    
    def upload_test_case(self, container_name, db_problem_id, test_number, input_data, output_data):
        input_blob_name = f"test_cases/{db_problem_id}/{test_number:02d}"
        output_blob_name = f"test_cases/{db_problem_id}/{test_number:02d}.a"
        try:
            input_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=input_blob_name)
            input_blob_client.upload_blob(input_data.encode('utf-8'), overwrite=True)
            logger.info(f"uploaded input test #{test_number}")
            
            output_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=output_blob_name)
            output_blob_client.upload_blob(output_data.encode('utf-8'), overwrite=True)
            logger.info(f"uploaded output test #{test_number}")
        except Exception as e:
            logger.error(f"upload failed for test {test_number}: {e}")
            raise
    
    def empty_blob(self, container_name, problem_id):
        prefix = f"test_cases/{problem_id}/"
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blobs_to_delete = [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]
            for blob_name in blobs_to_delete:
                container_client.delete_blob(blob_name)
            logger.info(f"deleted {len(blobs_to_delete)} files")
        except Exception as e:
            logger.error(f"delete failed: {e}")
            raise
    
    def upload_file(self, container_name, file_path, file_data):
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_path)
            blob_client.upload_blob(file_data, overwrite=True)
            logger.info(f"uploaded {file_path}")
        except Exception as e:
            logger.error(f"file upload error: {e}")
            raise


def get_storage_manager(storage_type=None):
    # get the right storage manager based on config
    from django.conf import settings
    
    if storage_type is None:
        storage_type = getattr(settings, 'STORAGE_TYPE', 'local')
    
    if storage_type == 'local':
        base_path = getattr(settings, 'LOCAL_STORAGE_PATH', None)
        if not base_path:
            base_path = os.path.join(settings.BASE_DIR, 'storage')
        return LocalStorageManager(base_path=base_path)
    
    elif storage_type == 'gdrive':
        credentials_path = getattr(settings, 'GDRIVE_CREDENTIALS_PATH', None)
        folder_id = getattr(settings, 'GDRIVE_FOLDER_ID', None)
        return GoogleDriveStorageManager(
            credentials_json_path=credentials_path,
            folder_id=folder_id
        )
    
    elif storage_type == 'r2':
        # Cloudflare R2 - FREE tier (10GB storage)
        return R2StorageManager(
            account_id=settings.R2_ACCOUNT_ID,
            access_key_id=settings.R2_ACCESS_KEY_ID,
            secret_access_key=settings.R2_SECRET_ACCESS_KEY
        )
    
    elif storage_type == 's3':
        return S3StorageManager(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=getattr(settings, 'AWS_REGION', 'us-east-1')
        )
    elif storage_type == 'azure':
        return AzureBlobManager(
            account_url=settings.AZURE_STORAGE_ACCOUNT_URL,
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            username=settings.AZURE_USERNAME,
            password=settings.AZURE_PASSWORD
        )
    else:
        raise ValueError(f"unknown storage type: {storage_type}")
